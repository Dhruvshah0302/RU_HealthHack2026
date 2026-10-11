# Deploying Call Bell Router on AWS (EC2 + CloudFront)

One small EC2 server runs the app (FastAPI + the built React pages). CloudFront sits in front
and gives a free **https://…cloudfront.net** link. HTTPS matters: browsers only allow the
microphone on HTTPS pages, and CloudFront also passes the dashboard's live WebSocket through.

Use region **us-west-2 (Oregon)** for everything, the same region as Bedrock.

## 0. Push the code first
The server installs from GitHub, so commit and push your latest work (never `.env`):
```
git pull
git add -A
git status            # .env must NOT be listed
git commit -m "Dashboard, Bedrock routing, deploy scripts"
git push
```

## 1. Launch the server (EC2 console > Launch instance)
| Setting | Value |
|---|---|
| Name | `callbell` |
| Image | Amazon Linux 2023 |
| Instance type | `t3.small` (t3.micro runs out of memory building the frontend) |
| Key pair | Proceed without a key pair (we use EC2 Instance Connect) |
| Network > Security group | Create: allow **HTTP (80)** from Anywhere and **SSH (22)** from Anywhere* |
| Advanced details > IAM instance profile | Leave empty, unless the workshop gives you one with Bedrock access (then you can skip the Bedrock key in step 3) |
| Advanced details > User data | Paste the whole of `deploy/ec2-user-data.sh` |

Launch, then wait about **5 minutes** while it installs and builds.

\* For a tighter setup after the demo works: HTTP only from the prefix list
`com.amazonaws.global.cloudfront.origin-facing`, SSH only from `com.amazonaws.us-west-2.ec2-instance-connect`.

## 2. Check it started
Instance > **Connect** > EC2 Instance Connect > Connect. In the browser terminal:
```
sudo tail -n 5 /var/log/callbell-setup.log     # ends with "systemctl enable --now callbell"
curl -s localhost/api/health                    # {"ok":true,...}
```

## 3. Add the secrets
Still in that terminal:
```
sudo nano /opt/callbell/src/.env
```
Paste the same lines as your laptop's `.env` (one per line, no quotes, nothing before the key):
```
ELEVENLABS_API_KEY=sk_...
ELEVENLABS_VOICE_ID=JBFqnCBsd6RMkjVDRZzb
AWS_BEARER_TOKEN_BEDROCK=bedrock-api-key-...
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=us.amazon.nova-2-lite-v1:0
```
Save (Ctrl+O, Enter, Ctrl+X), then:
```
sudo systemctl restart callbell
curl -s localhost/api/health      # "classifier" should now say bedrock, "voice" should be configured
```

## 4. Put CloudFront in front (CloudFront console > Create distribution)
| Setting | Value |
|---|---|
| Origin domain | The instance's **Public IPv4 DNS** (`ec2-…us-west-2.compute.amazonaws.com`) |
| Protocol | HTTP only, port 80 |
| Viewer protocol policy | Redirect HTTP to HTTPS |
| Allowed HTTP methods | GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE |
| Cache policy | **CachingDisabled** |
| Origin request policy | **AllViewer** |
| Web Application Firewall | Do not enable |

Create, wait until "Deploying" finishes (5–10 min), then open:
- Patient: `https://<your-id>.cloudfront.net/patient?room=412`
- Dashboard: `https://<your-id>.cloudfront.net/dashboard`

## Updating after new pushes
```
sudo bash /opt/callbell/src/deploy/update.sh
```
A restart clears the tickets (they are kept in memory).

## Things to know
- **Do not stop the instance.** Its public DNS changes on restart and CloudFront would lose it.
  (Rebooting is fine; or attach an Elastic IP.)
- **The Bedrock short-term API key expires** (12 hours at most). If tickets start saying
  "classifier failed", make a new key, update `.env` on the server, restart.
- **Workshop accounts** are usually deleted after the event, and may block CloudFront or some
  instance types. If CloudFront is blocked, `http://<public IP>/` still works, but the browser
  will block the microphone (typing still works).
- **No login.** Anyone with the link can see the dashboard. The patient data is synthetic, so
  that is fine for the demo, but don't share the link publicly.
