####
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
####
import boto3
import sys
import argparse

AWS_REGION = "ca-central-1"

parser = argparse.ArgumentParser()
parser.add_argument('-p', '--profile', help="AWS profile name to use to run this command")
parser.add_argument("-m", '--mode', choices=["run", "test"], help="Type 'run' to execute or 'test' to simulate")
if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(0)
args = parser.parse_args()

session = boto3.session.Session(
    profile_name=args.profile
)

default_filter = {
    "Name": "isDefault",
    "Values": ["true"]
}

clean_run = True
ec2 = session.client('ec2', region_name=AWS_REGION)
for region in ec2.describe_regions()["Regions"]:
    print("Working through region " + region["RegionName"])
    ec2r = session.resource(
        'ec2',
        region_name=region["RegionName"],
    )
    found_default = False
    for vpc in ec2r.vpcs.filter(Filters=[default_filter]):
        found_default = True
        dependancies = False
        for instance in vpc.instances.all():
            print("!! Default VPC " + vpc.id + " has running instance " + instance.id + ".  Terminate and retry.")
            dependancies = True
        for network_interface in vpc.network_interfaces.all():
            print(
                "!! Default VPC " + vpc.id + " has network interfaces " + network_interface.id + ".  Delete and retry.")
            dependancies = True
        for accepted_vpc_peering_connection in vpc.accepted_vpc_peering_connections.all():
            print(
                "!! Default VPC " + vpc.id + " has accepted VPC peering connections " + accepted_vpc_peering_connection.id + ".  Delete and retry.")
            dependancies = True
        for requested_vpc_peering_connection in vpc.requested_vpc_peering_connections.all():
            print(
                "!! Default VPC " + vpc.id + " has requested VPC peering connections " + requested_vpc_peering_connection.id + ".  Delete and retry.")
            dependancies = True
        if dependancies:
            clean_run = False
            continue
        resources_clear = True
        for resource in ["internet_gateways", "subnets", "route_tables", "network_acls", "security_groups"]:
            for collection in vpc.__getattribute__(resource).all():
                if resource == "internet_gateways":
                    print(".. Detaching internet gateway: " + collection.id)
                    try:
                        if args.mode == "test":
                            print("-- Running in test mode.  Detach not issued")
                        else:
                            collection.detach_from_vpc(VpcId=vpc.id)
                    except Exception as e:
                        print("!! Exception: " + str(e))
                        resources_clear = False
                if resource == "route_tables":
                    if collection.associations_attribute[0]["Main"]:
                        continue
                if resource == "network_acls":
                    if collection.is_default:
                        continue
                if resource == "security_groups":
                    if collection.group_name == "default":
                        continue
                print(".. Deleting " + resource + ": " + collection.id)
                try:
                    if args.mode == "test":
                        print("-- Running in test mode.  Delete not issued")
                    else:
                        collection.delete()
                except Exception as e:
                    print("!! Exception " + str(e))
                    resources_clear = False
        if resources_clear:
            print(".. Deleting VPC : " + vpc.id)
            try:
                if args.mode == "test":
                    print("-- Running in test mode.  Delete not issued")
                else:
                    vpc.delete()
            except Exception as e:
                print("!! Exception " + str(e))
    if not found_default:
        print(".. No default VPC found")

if clean_run:
    sys.exit(0)
else:
    sys.exit(1)
