'use strict';

console.log('Loading function');

var AWS = require('aws-sdk');


//  Lookup an AMI in the given region 
//  based on the given metadata (description, etc.)
function amiLookup(region, metadata) {

    //  Make EC2 client pointing at the given region:
    var ec2_region = new AWS.EC2({'region': region});

    // Lookup in the given retion using metadata:
    var params = {
      Filters: [
        {Name: 'architecture', Values: [metadata.Architecture]},
        {Name: 'image-type', Values: [metadata.ImageType]},
        {Name: 'owner-alias', Values: [metadata.ImageOwnerAlias]},
        {Name: 'description', Values: [metadata.Description]},
        {Name: 'root-device-type', Values: [metadata.RootDeviceType]},
        {Name: 'virtualization-type', Values: [metadata.VirtualizationType]},
        {Name: 'hypervisor', Values: [metadata.Hypervisor]}
      ]              
    };
  
    // This "Promise" makes it so we can later retrieve the results:
    return new Promise(function(resolve, reject) {
  
        // Find matching image in the east:
        ec2_region.describeImages(params, function(err, data) {
          if (err) { 
              console.log(err, err.stack); 
              return reject(err);
          } else { 
              if ( data.Images.size < 1 ) {
                  console.log('No matching image found in ' + region); 
                  return reject('No matching image found in ' + region);
              } else {
                  console.log("returned image for " + region + " is: " + data.Images[0].ImageId);
                  resolve ( { [region]:{"ami": data.Images[0].ImageId}});
              }
          }
        });
    });  
}


/**
 * Return a region mapping json structure, suitable for use
 * in a CloudFormation template.
 */
exports.handler = (event, context, callback) => {
    console.log('Received event:', JSON.stringify(event, null, 2));

    const done = (err, res) => callback(null, {
        statusCode: err ? '400' : '200',
        body: err ? err.message : res,
        headers: {
            'Content-Type': 'application/json',
        },
    });

    if ( !event.region ) { 
        done({'message': 'Region is required input.'});  
        return;
    }         
    if ( !event.ami ) { 
        done({'message': 'AMI is required input.'});  
        return;
    }  

    
    //  Step 1: Define an EC2 client pointing at the given region:
    var ec2_region = new AWS.EC2({'region': event.region});

    //  Step 2: Describe the given AMI:
    var params = {
      ImageIds: [event.ami /* AMI entered by the user. */  ]
    };
    ec2_region.describeImages(params, function(err, data) {
        if (err) { 
            console.log(err, err.stack); 
        } else { 
            if ( data.Images.size < 1 ) {
              done({'message': 'No image found for ID = ' + event.ami});           
            } else {
              //    This code assumes 1 and only 1 match 
              //    for the AMI ID.  Seems like a safe assumption...
              var img = data.Images[0];
              
              //    Step 3:  Using the metadata returned on the given AMI,
              //    Asynchronously search for the matching AMI in all 
              //    of the other regions:
                var promises = [];
                promises.push(amiLookup("us-east-1", img));
                promises.push(amiLookup("us-east-2", img));
                promises.push(amiLookup("us-west-1", img));
                promises.push(amiLookup("us-west-2", img));
        //        promises.push(amiLookup("eu-west-1", img));  // Opt-in required?
        //        promises.push(amiLookup("eu-west-2", img));
                promises.push(amiLookup("ap-southeast-1", img));
                promises.push(amiLookup("ap-southeast-2", img));
                promises.push(amiLookup("ap-northeast-1", img));
                promises.push(amiLookup("ap-northeast-2", img));
                
                //  Step 4:  Collect results:
                Promise.all(promises).then(function(collected) {
                    done(null,collected);
                }, function(err) {
                    done({'message': err});           
                });              
              
            } 
        }
    });
};
