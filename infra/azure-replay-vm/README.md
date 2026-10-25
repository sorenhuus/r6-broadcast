# Replay VM (Azure)

A Windows 11 VM with an A10 GPU slice that runs the Siege replay viewer and the r6cast capture agent. It is kept separate from your gaming PC and main account.

## Deploy

```bash
cd infra/azure-replay-vm
cat > terraform.tfvars <<EOF
subscription_id      = "<sub-id>"
admin_password       = "<strong password>"
allowed_source_cidrs = ["<your home ip>/32"]
EOF
terraform init && terraform apply
```

Check quota first: `az vm list-usage -l swedencentral -o table | grep -i NVADS`. A10 v5 often needs a quota request.

Cost: NV12ads_A10_v5 on Spot is roughly $0.3–1/h, and about $1.8/h on regular pricing. You also pay for the 256 GB Premium disk while the VM is stopped. The VM shuts down every night at 01:00. Stop it after a session with `az vm deallocate`.

## One-time setup over RDP

1. **Sign in to Steam and Ubisoft Connect** with the second Siege account. Siege X is free to play, so the account needs no purchase. Install Siege (~90 GB).
2. **Launch Siege once**, set windowed 1920x1080, and open any replay to check the viewer works.
3. **Agent code (repo is private):** clone it on the VM with your GitHub login, or copy it over, into `C:\r6cast\repo`. Then run `pip install -e C:\r6cast\repo[capture]`.
4. **OBS:** turn on Tools → WebSocket Server Settings (port 4455) and set the password in `C:\r6cast\capture.toml` (copy `capture.example.toml`).
5. **Claude desktop app:** install it on the VM and link it to the session. Claude can then drop jobs into `C:\r6cast\jobs` and collect the recordings.

## Replays

Copy a match folder from your PC (`...\Tom Clancy's Rainbow Six Siege\MatchReplay\Match-...`) into the same folder on the VM. The first test is whether the viewer opens another account's replay.
