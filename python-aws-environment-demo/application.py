from flask import Flask, flash, redirect, render_template, request, session, abort
from ec2_metadata import ec2_metadata

# Must be named 'application' for Beanstalk to work:
application = Flask(__name__)

@application.route("/")
def index():

  dflt = "-NA- (Not running on EC2 instance) ...."
  metadata = {}
  metadata['region'] = dflt
  metadata['instanceId'] = dflt
  metadata['instanceType'] = dflt
  metadata['amiId'] = dflt
  metadata['instanceAction'] = dflt
  metadata['localIpv4'] = dflt
  metadata['localHostname'] = dflt
  metadata['publicIpv4'] = dflt
  metadata['publicHostname'] = dflt
  metadata['hostname'] = dflt
  metadata['mac'] = dflt
  metadata['reservationId'] = dflt
  metadata['securityGroups'] = dflt
  metadata['availabilityZone'] = dflt

  try:
    metadata['region'] = ec2_metadata.region
    metadata['instanceId'] = ec2_metadata.instance_id
    metadata['instanceType'] = ec2_metadata.instance_type
    metadata['amiId'] = ec2_metadata.ami_id
    metadata['instanceAction'] = ec2_metadata.instance_action
    metadata['localIpv4'] = ec2_metadata.private_ipv4
    metadata['localHostname'] = ec2_metadata.private_hostname
    metadata['publicIpv4'] = ec2_metadata.public_ipv4
    metadata['publicHostname'] = ec2_metadata.public_hostname
    metadata['hostname'] = ec2_metadata.public_hostname
    metadata['mac'] = ec2_metadata.mac
    metadata['reservationId'] = ec2_metadata.reservation_id
    metadata['securityGroups'] = ec2_metadata.security_groups
    metadata['availabilityZone'] = ec2_metadata.availability_zone
  except BaseException as e:
    print("Looks like instance metadata is not available, substituting...")
    print("Metadata lookup error: {0}".format(e))


  return render_template(
      'environment.html',**locals())


if __name__ == "__main__":
    # app.run(host='0.0.0.0', port=5000)
    application.run()