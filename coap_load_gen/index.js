const coap = require('coap');
const cbor = require('cbor');
const uuidv4 = require('uuid/v4');
const async = require('async')

function sendCoap(payload) {

    var obj = {
        // replace hostname value with the IP of the remote machine
        hostname: "10.2.5.14", //  fe80::2ba3:a945:c80f:31e8 rpi fe80::ba27:ebff:fe84:ae79 aj fe80::1d36:8b5d:bc44:5cad
        port: 5683,
        pathname: "other/sensor-values",
        method: 'POST',
    };

    var req = coap.request(obj)
    req.write(cbor.encode(payload));
    // Uncomment this code if you want response from the receiver
    // req.on('response', function (res) {
    //  res.pipe(process.stdout)
    //  res.on('end', function () {
    //      //console.log("sent to CoAP")
    //  })
    // })

    req.end()
}

task = [
            // function (callback) {
            //  setTimeout(callback, 1000);
            // },
            function (callback) {
                run()
                callback()
            }
        ]


function runF(seconds) {
    console.log("Running forever ...")

    var delay = 100; // delay in msec. 100 corresponds to 100/1000 sec
    async.forever(
        function(next) {
            run()


            if(seconds) {
                dt = new Date();
         
                if((dt - startTime)/1000 > seconds){ // seconds
                    console.log("Exiting at:", dt, " | Sent: ", totalSent, "meesages.")
                    process.exit()
                }
            }    
            //Repeat after the delay
            setTimeout(function() {
            next();
            }, delay)

        },
        function(err) {
            // if next is called with a value in its first parameter, it will appear
            // in here as 'err', and execution will stop.
        }
    );
}

function getRead() {
    var luxReading = new Object;
    luxReading.lux = 234.1
    luxReading.lux = Math.floor(Math.random() * (13000.0 - 0.1 + 1)) + 0.1;
     

    dt = new Date()
    rkey = uuidv4()

    var tempPayload = new Object;
    tempPayload.asset = 'TI sensorTag/luxometer'
    tempPayload.sensor_values = luxReading
    tempPayload.key = rkey
    tempPayload.timestamp = dt.toISOString()
    // console.log(tempPayload)
    return tempPayload

}
function run() {
        lux_read = getRead()
        sendCoap(lux_read)
        totalSent++

}

totalSent = 0
startTime =  new Date()
console.log("Started at:", startTime)

runF(15*60);