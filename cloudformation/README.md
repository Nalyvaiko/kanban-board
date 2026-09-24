# Deploying to AWS

This puts the kanban board on one small AWS server (EC2 instance). It's the
cheapest way to run it on AWS — usually free for the first year on a new
AWS account, and about $8-15/month after that.

## Quick start

1. **Install and set up the AWS CLI.** If you don't have it yet: [install
   instructions](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
   Then run `aws configure` and enter your AWS access key.

2. **Make sure the GitHub repo is public.** The server downloads the code
   over the internet with no login, so it needs to be a public repo.

3. **Find two IDs you'll need** (copy-paste these commands):

   ```sh
   # Your VPC ID
   aws ec2 describe-vpcs --filters Name=is-default,Values=true --query 'Vpcs[0].VpcId' --output text

   # A subnet ID inside that VPC (use the VPC ID from above)
   aws ec2 describe-subnets --filters Name=vpc-id,Values=<paste-vpc-id-here> Name=map-public-ip-on-launch,Values=true --query 'Subnets[0].SubnetId' --output text
   ```

4. **Run the deploy command**, using the two IDs from step 3:

   ```sh
   aws cloudformation deploy \
     --template-file cloudformation/template.yaml \
     --stack-name kanban-board \
     --parameter-overrides \
         VpcId=<paste-vpc-id-here> \
         SubnetId=<paste-subnet-id-here> \
         SshLocation=$(curl -s ifconfig.me)/32 \
     --capabilities CAPABILITY_IAM
   ```

   This takes a couple of minutes to finish.

5. **Wait a few more minutes**, then get your app's web address:

   ```sh
   aws cloudformation describe-stacks --stack-name kanban-board \
     --query 'Stacks[0].Outputs' --output table
   ```

   Look for `AppUrl` in the output and open it in your browser. The extra
   wait after step 4 is because the server is still installing Docker and
   building the app in the background — if the page doesn't load yet, just
   wait a bit and refresh.

6. **When you're done and want to stop paying for it:**

   ```sh
   aws cloudformation delete-stack --stack-name kanban-board
   ```

   This deletes everything the deploy created — nothing is left running
   or billing you afterward.

That's it. Everything below is background info you don't need to read to
get it running, but is useful if something goes wrong or you want to know
what you're paying for.

## If the page doesn't load

Get a shell on the server (no password or SSH key needed) and check the
setup log:

```sh
aws ssm start-session --target <InstanceId-from-the-outputs-table>
sudo tail -f /var/log/user-data.log
```

## Updating after a code change

The server only builds the app once, when it first starts. To pick up new
code, get a shell on it (see above) and run:

```sh
cd /opt/kanban-board && git pull && docker compose up -d --build
```

Or just delete the stack (step 6) and deploy again — that gives you a
fresh server running the latest code.

## What you're trading for the low cost

- **The database can be lost.** The data lives on the server's disk. It
  survives a restart, but not if the server itself ever gets replaced.
  Fine for a demo or personal project; not something you'd want for real
  user data.
- **No HTTPS.** The app is plain `http://`, not `https://`. Adding HTTPS
  needs a domain name, which this setup doesn't assume you have.
- **One server, no backup.** If it goes down, the app goes down with it.

If any of that becomes a problem, the fix is a more expensive setup:
a real database (AWS RDS) instead of one running on the server, and/or a
managed hosting service (AWS App Runner) instead of a plain server. Ask
if you want that version built too.
