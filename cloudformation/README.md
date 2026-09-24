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
     --capabilities CAPABILITY_NAMED_IAM
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

If you've set up automatic deploys (below), just push to `main` — it
handles this for you. To update by hand instead:

```sh
aws ssm start-session --target <InstanceId-from-the-outputs-table>
cd /opt/kanban-board && git pull && docker compose up -d --build
```

Or just delete the stack (step 6) and deploy again — that gives you a
fresh server running the latest code.

## Automatic deploys (CI/CD)

`.github/workflows/ci-cd.yml` runs the backend and frontend tests, then
the integration and end-to-end tests against a real `docker compose`
stack, and — only if all of that passes, and only on a push to `main` —
deploys to AWS and checks the app came back up healthy. It authenticates
to AWS the safe way: no long-lived AWS keys stored in GitHub, just a
role GitHub proves it's allowed to use for a few minutes at a time
(this is called OIDC).

One-time setup, before this will work:

1. **Deploy the role GitHub Actions will use** (only needs to be done
   once, ever, for this repo):

   ```sh
   aws cloudformation deploy \
     --template-file cloudformation/github-oidc.yaml \
     --stack-name kanban-board-github-oidc \
     --capabilities CAPABILITY_NAMED_IAM
   ```

   If this fails with something like "OIDC provider already exists",
   your AWS account already has one from another project — redeploy
   with `--parameter-overrides CreateOidcProvider=false ExistingOidcProviderArn=<its ARN>`
   instead (find it with `aws iam list-open-id-connect-providers`).

2. **Get the role's ARN:**

   ```sh
   aws cloudformation describe-stacks --stack-name kanban-board-github-oidc \
     --query 'Stacks[0].Outputs[?OutputKey==`DeployRoleArn`].OutputValue' --output text
   ```

3. **Add these as variables in your GitHub repo** (Settings → Secrets
   and variables → Actions → Variables tab — they're not secret, so
   variables, not secrets, are the right place):

   | Variable | Value |
   | --- | --- |
   | `AWS_DEPLOY_ROLE_ARN` | the ARN from step 2 |
   | `AWS_REGION` | e.g. `us-east-1` |
   | `AWS_STACK_NAME` | `kanban-board` (or whatever you used in the quick start) |
   | `AWS_VPC_ID` | your VPC ID from the quick start |
   | `AWS_SUBNET_ID` | your subnet ID from the quick start |

That's it — the next push to `main` will deploy automatically. If the
app stack (`AWS_STACK_NAME`) doesn't exist yet, the workflow creates it;
if it already exists (you ran the quick start by hand first), the
workflow updates the running instance in place instead of replacing it,
so its data isn't lost.

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
