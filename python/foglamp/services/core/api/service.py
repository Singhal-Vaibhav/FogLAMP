# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio
import datetime
from aiohttp import web
import uuid

from foglamp.common import utils
from foglamp.common import logger
from foglamp.common.service_record import ServiceRecord
from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.common.storage_client.exceptions import StorageServerError
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.services.core import server
from foglamp.services.core import connect
from foglamp.services.core.api import utils as apiutils
from foglamp.services.core.scheduler.entities import StartUpSchedule
from foglamp.services.core.service_registry.service_registry import ServiceRegistry
from foglamp.services.core.service_registry import exceptions as service_registry_exceptions


__author__ = "Mark Riddoch, Ashwin Gopalakrishnan, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------------
    | GET POST            | /foglamp/service                                      |
    -------------------------------------------------------------------------------
"""

_logger = logger.setup()

#################################
#  Service
#################################


def get_service_records():
    sr_list = list()
    for service_record in ServiceRegistry.all():
        sr_list.append(
            {
                'name': service_record._name,
                'type': service_record._type,
                'address': service_record._address,
                'management_port': service_record._management_port,
                'service_port': service_record._port,
                'protocol': service_record._protocol,
                'status': ServiceRecord.Status(int(service_record._status)).name.lower()
            })
    recs = {'services': sr_list}
    return recs


async def get_health(request):
    """
    Args:
        request:

    Returns:
            health of all registered services

    :Example:
            curl -X GET http://localhost:8081/foglamp/service
    """
    response = get_service_records()
    return web.json_response(response)


async def delete_service(request):
    """ Delete an existing service

    :Example:
        curl -X DELETE http://localhost:8081/foglamp/service/<svc name>
    """

    try:
        svc = request.match_info.get('service_name', None)

        if svc is None or svc.strip() == '':
            raise web.HTTPBadRequest(reason='Missing service_name in requested URL')

        storage = connect.get_storage_async()

        result = await get_schedule(storage, svc)
        if result['count'] == 0:
            raise web.HTTPBadRequest(reason='A service with this name does not exist.')

        svc_schedule = result['rows'][0]
        sch_id = uuid.UUID(svc_schedule['id'])
        if svc_schedule['enabled'].lower() == 't':
            # disable it
            await server.Server.scheduler.disable_schedule(sch_id)
        # delete it
        await server.Server.scheduler.delete_schedule(sch_id)

        # delete all configuration for the service name
        await delete_configuration(storage, svc)

        try:
            ServiceRegistry.get(name=svc)
        except service_registry_exceptions.DoesNotExist:
            pass
        else:
            # shutdown of service does not actually remove it from service registry via unregister (it just set its
            # status to Shutdown)
            while True:
                svcs = ServiceRegistry.get(name=svc)
                if svcs[0]._status == ServiceRecord.Status.Shutdown:
                    ServiceRegistry.remove_from_registry(svcs[0]._id)
                    break
                else:
                    await asyncio.sleep(1.0)
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=ex)
    else:
        return web.json_response({'result': 'Service {} deleted successfully.'.format(svc)})


async def add_service(request):
    """
    Create a new service to run a specific plugin

    :Example:
             curl -X POST http://localhost:8081/foglamp/service -d '{"name": "DHT 11", "plugin": "dht11", "type": "south", "enabled": true}'
             curl -sX POST http://localhost:8081/foglamp/service -d '{"name": "Sine", "plugin": "sinusoid", "type": "south", "enabled": true, "config": {"dataPointsPerSec": {"value": "10"}}}' | jq
    """

    try:
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError('Data payload must be a valid JSON')

        name = data.get('name', None)
        plugin = data.get('plugin', None)
        service_type = data.get('type', None)
        enabled = data.get('enabled', None)
        config = data.get('config', None)

        if name is None:
            raise web.HTTPBadRequest(reason='Missing name property in payload.')
        if plugin is None:
            raise web.HTTPBadRequest(reason='Missing plugin property in payload.')
        if service_type is None:
            raise web.HTTPBadRequest(reason='Missing type property in payload.')
        if utils.check_reserved(name) is False:
            raise web.HTTPBadRequest(reason='Invalid name property in payload.')
        if utils.check_reserved(plugin) is False:
            raise web.HTTPBadRequest(reason='Invalid plugin property in payload.')

        service_type = str(service_type).lower()
        if service_type == 'north':
            raise web.HTTPNotAcceptable(reason='north type is not supported for the time being.')
        if service_type not in ['south']:
            raise web.HTTPBadRequest(reason='Only south type is supported.')
        if enabled is not None:
            if enabled not in ['true', 'false', True, False]:
                raise web.HTTPBadRequest(reason='Only "true", "false", true, false'
                                                ' are allowed for value of enabled.')
        is_enabled = True if ((type(enabled) is str and enabled.lower() in ['true']) or (
            (type(enabled) is bool and enabled is True))) else False

        # Check if a valid plugin has been provided
        try:
            # "plugin_module_path" is fixed by design. It is MANDATORY to keep the plugin in the exactly similar named
            # folder, within the plugin_module_path.
            # if multiple plugin with same name are found, then python plugin import will be tried first
            plugin_module_path = "foglamp.plugins.south" if service_type == 'south' else "foglamp.plugins.north"
            import_file_name = "{path}.{dir}.{file}".format(path=plugin_module_path, dir=plugin, file=plugin)
            _plugin = __import__(import_file_name, fromlist=[''])

            script = '["services/south"]' if service_type == 'south' else '["services/north"]'
            # Fetch configuration from the configuration defined in the plugin
            plugin_info = _plugin.plugin_info()
            if plugin_info['type'] != service_type:
                msg = "Plugin of {} type is not supported".format(plugin_info['type'])
                _logger.exception(msg)
                return web.HTTPBadRequest(reason=msg)
            plugin_config = plugin_info['config']
            process_name = 'south'
        except ImportError as ex:
            # Checking for C-type plugins
            script = '["services/south_c"]' if service_type == 'south' else '["services/north_c"]'
            plugin_info = apiutils.get_plugin_info(plugin)
            if plugin_info['type'] != service_type:
                msg = "Plugin of {} type is not supported".format(plugin_info['type'])
                _logger.exception(msg)
                return web.HTTPBadRequest(reason=msg)
            plugin_config = plugin_info['config']
            process_name = 'south_c'
            if not plugin_config:
                _logger.exception("Plugin %s import problem from path %s. %s", plugin, plugin_module_path, str(ex))
                raise web.HTTPNotFound(reason='Plugin "{}" import problem from path "{}".'.format(plugin, plugin_module_path))
        except Exception as ex:
            _logger.exception("Failed to fetch plugin configuration. %s", str(ex))
            raise web.HTTPInternalServerError(reason='Failed to fetch plugin configuration')

        storage = connect.get_storage_async()
        config_mgr = ConfigurationManager(storage)

        # Check that the schedule name is not already registered
        count = await check_schedules(storage, name)
        if count != 0:
            raise web.HTTPBadRequest(reason='A service with this name already exists.')

        # Check that the process name is not already registered
        count = await check_scheduled_processes(storage, process_name)
        if count == 0:
            # Now first create the scheduled process entry for the new service
            payload = PayloadBuilder().INSERT(name=process_name, script=script).payload()
            try:
                res = await storage.insert_into_tbl("scheduled_processes", payload)
            except StorageServerError as ex:
                _logger.exception("Failed to create scheduled process. %s", ex.error)
                raise web.HTTPInternalServerError(reason='Failed to create service.')
            except Exception as ex:
                _logger.exception("Failed to create scheduled process. %s", str(ex))
                raise web.HTTPInternalServerError(reason='Failed to create service.')

        # If successful then create a configuration entry from plugin configuration
        try:
            # Create a configuration category from the configuration defined in the plugin
            category_desc = plugin_config['plugin']['description']
            await config_mgr.create_category(category_name=name,
                                             category_description=category_desc,
                                             category_value=plugin_config,
                                             keep_original_items=True)
            # Create the parent category for all South services
            await config_mgr.create_category("South", {}, "South microservices", True)
            await config_mgr.create_child_category("South", [name])

            # If config is in POST data, then update the value for each config item
            if config is not None:
                if not isinstance(config, dict):
                    raise ValueError('Config must be a JSON object')
                for k, v in config.items():
                    await config_mgr.set_category_item_value_entry(name, k, v['value'])

        except Exception as ex:
            await delete_configuration(storage, name)  # Revert configuration entry
            _logger.exception("Failed to create plugin configuration. %s", str(ex))
            raise web.HTTPInternalServerError(reason='Failed to create plugin configuration.')

        # If all successful then lastly add a schedule to run the new service at startup
        try:
            schedule = StartUpSchedule()
            schedule.name = name
            schedule.process_name = process_name
            schedule.repeat = datetime.timedelta(0)
            schedule.exclusive = True
            #  if "enabled" is supplied, it gets activated in save_schedule() via is_enabled flag
            schedule.enabled = False

            # Save schedule
            await server.Server.scheduler.save_schedule(schedule, is_enabled)
            schedule = await server.Server.scheduler.get_schedule_by_name(name)
        except StorageServerError as ex:
            await delete_configuration(storage, name)  # Revert configuration entry
            _logger.exception("Failed to create schedule. %s", ex.error)
            raise web.HTTPInternalServerError(reason='Failed to create service.')
        except Exception as ex:
            await delete_configuration(storage, name)  # Revert configuration entry
            _logger.exception("Failed to create service. %s", str(ex))
            raise web.HTTPInternalServerError(reason='Failed to create service.')

    except ValueError as e:
        raise web.HTTPBadRequest(reason=str(e))
    else:
        return web.json_response({'name': name, 'id': str(schedule.schedule_id)})


async def check_scheduled_processes(storage, process_name):
    payload = PayloadBuilder().SELECT("name").WHERE(['name', '=', process_name]).payload()
    result = await storage.query_tbl_with_payload('scheduled_processes', payload)
    return result['count']


async def check_schedules(storage, schedule_name):
    payload = PayloadBuilder().SELECT("schedule_name").WHERE(['schedule_name', '=', schedule_name]).payload()
    result = await storage.query_tbl_with_payload('schedules', payload)
    return result['count']


async def get_schedule(storage, schedule_name):
    payload = PayloadBuilder().SELECT(["id", "enabled"]).WHERE(['schedule_name', '=', schedule_name]).payload()
    result = await storage.query_tbl_with_payload('schedules', payload)
    return result


async def delete_configuration(storage, key):
    await delete_configuration_category(storage, key)
    await delete_configuration_category(storage, "{}Advanced".format(key))
    await delete_parent_child_configuration(storage, key)
    await delete_advance_child_configuration(storage, key)


async def delete_configuration_category(storage, key):
    payload = PayloadBuilder().WHERE(['key', '=', key]).payload()
    await storage.delete_from_tbl('configuration', payload)

    # Removed key from configuration cache
    config_mgr = ConfigurationManager(storage)
    config_mgr._cacheManager.remove(key)


async def delete_parent_child_configuration(storage, key):
    payload = PayloadBuilder().WHERE(['parent', '=', "South"]).AND_WHERE(['child', '=', key]).payload()
    await storage.delete_from_tbl('category_children', payload)


async def delete_advance_child_configuration(storage, key):
    payload = PayloadBuilder().WHERE(['parent', '=', key]).payload()
    await storage.delete_from_tbl('category_children', payload)
