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
deploys to AWS and checks the app came back up healthy.

It authenticates with a plain IAM access key stored as GitHub secrets.
That's not the ideal way to do this - a long-lived key that doesn't
expire is a real, if small, security downgrade compared to the
alternative (OIDC: GitHub proves who it is and gets a credential that's
only valid for a few minutes, nothing stored). The workflow defaults to
access keys because that alternative needs your AWS account to allow
creating an OIDC provider, and **some accounts don't**: any account
created through a guided "project" setup wizard may belong to an AWS
Organization whose Service Control Policy explicitly blocks
`iam:CreateOpenIDConnectProvider` account-wide - no permission inside
the account can override that, only someone with access to the
*management* account (a separate, higher-level account) editing or
removing that policy can. If you don't have that access - and if you
didn't set this AWS account up as part of an organization yourself,
you probably don't - the access-key path below is what actually works.

**If your account does allow it**, prefer OIDC instead: deploy
`cloudformation/github-oidc.yaml` (see the comment at the top of
`ci-cd.yml`'s deploy job for the couple of one-line changes that
switches it over) rather than following the steps below.

One-time setup for the access-key path, before automatic deploys will work:

1. **Create the IAM user GitHub Actions will use** (only needs to be
   done once, ever, for this repo):

   ```sh
   aws cloudformation deploy \
     --template-file cloudformation/github-deploy-user.yaml \
     --stack-name kanban-board-github-deploy-user \
     --capabilities CAPABILITY_NAMED_IAM
   ```

2. **Create an access key for that user.** Deliberately not something
   CloudFormation does for you - a stack output stays readable by
   anyone who can read the stack for as long as it exists, a bad place
   for a secret to live even briefly. This instead prints it exactly
   once, right here:

   ```sh
   aws iam create-access-key --user-name kanban-board-github-deploy-user
   ```

   Copy the `AccessKeyId` and `SecretAccessKey` from the output now -
   you cannot retrieve the secret again later (you'd have to delete
   this key and create a new one).

3. **Add these to your GitHub repo** (Settings → Secrets and variables
   → Actions): `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` on the
   **Secrets** tab (these two are genuinely sensitive), the rest on the
   **Variables** tab:

   | Name | Tab | Value |
   | --- | --- | --- |
   | `AWS_ACCESS_KEY_ID` | Secret | from step 2 |
   | `AWS_SECRET_ACCESS_KEY` | Secret | from step 2 |
   | `AWS_REGION` | Variable | e.g. `us-east-1` |
   | `AWS_STACK_NAME` | Variable | `kanban-board` (or whatever you used in the quick start) |
   | `AWS_VPC_ID` | Variable | your VPC ID from the quick start |
   | `AWS_SUBNET_ID` | Variable | your subnet ID from the quick start |

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
