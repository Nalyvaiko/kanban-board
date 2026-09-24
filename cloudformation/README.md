# cloudformation

Deploys the kanban board to AWS as cheaply as this app can reasonably run:
one EC2 instance, running the exact `docker-compose.yaml` already in this
repo (app + Postgres containers together, on the same box). No load
balancer, no managed database, no VPC of its own.

**What this trades away for the low cost**, so you can decide if it's
right for your use: the Postgres data lives on the instance's disk - it's
fine across reboots (the `restart: unless-stopped` policies bring both
containers back up), but gone if the instance itself is ever replaced or
terminated. There's no HTTPS (the app is reachable over plain HTTP on port
8000) since that needs a domain name to get a certificate for. There's no
auto-scaling or failover. If you outgrow any of that, the natural next
step is Postgres on RDS instead of in a container (durable, backed up)
and/or the app on AWS App Runner instead of raw EC2 (managed, built-in
HTTPS) - meaningfully more moving parts and cost, which is why this
template doesn't default to it.

**Estimated cost**: ~$0-8/month on a new AWS account's free tier
(t3.micro, 750 free hours/month for 12 months) covers the instance; the
20GB gp3 EBS volume (~$1.60/mo) and the Elastic IP (free while attached to
a running instance) are the main things free tier doesn't cover. Off free
tier, budget roughly $8-15/month for a t3.micro.

## Prerequisites

- An AWS account and the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), configured with credentials (`aws configure`).
- **This repo must be public** on GitHub (or wherever `RepoUrl` points) - the instance clones it over plain HTTPS with no credentials. If it's private, either make it public, or adjust the template's `UserData` to authenticate (e.g. a fine-grained deploy token).
- The branch/tag you pass as `GitRef` needs `Dockerfile` and `docker-compose.yaml` at its root - i.e. these changes need to be merged (or point `GitRef` at this specific branch to try it before merging).
- Your account's default VPC ID and a public subnet in it (any VPC works, but the default VPC is the path of least resistance if you haven't set up your own):

  ```sh
  aws ec2 describe-vpcs --filters Name=is-default,Values=true --query 'Vpcs[0].VpcId' --output text
  aws ec2 describe-subnets --filters Name=vpc-id,Values=<VpcId> Name=map-public-ip-on-launch,Values=true --query 'Subnets[0].SubnetId' --output text
  ```

- Optional, only if you want SSH access instead of (or alongside) SSM: an EC2 key pair (`aws ec2 create-key-pair --key-name kanban-board --query KeyMaterial --output text > kanban-board.pem && chmod 400 kanban-board.pem`).

## Deploy

```sh
aws cloudformation deploy \
  --template-file cloudformation/template.yaml \
  --stack-name kanban-board \
  --parameter-overrides \
      VpcId=<your-vpc-id> \
      SubnetId=<your-subnet-id> \
      SshLocation=$(curl -s ifconfig.me)/32 \
  --capabilities CAPABILITY_IAM
```

(`CAPABILITY_IAM` is required because the template creates an IAM role for
SSM access - see `template.yaml`'s `InstanceRole`.) Add `KeyName=<your-key-pair-name>`
to the overrides if you created one.

This takes a couple of minutes for the stack itself, then a few minutes
more before the app responds - the instance's first boot installs Docker,
clones the repo, and runs `docker compose up -d --build`, which builds the
frontend from source. Get the URL once it's done:

```sh
aws cloudformation describe-stacks --stack-name kanban-board \
  --query 'Stacks[0].Outputs' --output table
```

Open `AppUrl`. If it's not responding yet, check progress via the
`SsmCommand` output (no key pair needed) and the `BuildLogCommand` it
prints, or SSH in with `SshCommand` if you set `KeyName`.

## Updating

`docker compose up -d --build` only ran once, on first boot - a new stack
deploy alone won't pick up code changes on an existing instance. Either
SSM/SSH in and re-run `cd /opt/kanban-board && git pull && docker compose up -d --build`,
or delete and redeploy the stack for a clean instance on the latest `GitRef`.

## Tearing it down

```sh
aws cloudformation delete-stack --stack-name kanban-board
```

This removes the instance, its EBS volume, the Elastic IP, and the IAM
role/security group - nothing in this template persists outside the
stack itself (that's the durability tradeoff described above: there's no
separate database to accidentally leave running and paying for).
