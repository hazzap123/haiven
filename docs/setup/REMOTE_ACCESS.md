# Remote access

The hub lives in the person's house; you and the carers mostly do not. Two kinds of remote access are needed, and they solve different problems:

| Need | What it is for | Recommended |
|---|---|---|
| **Carers' phones** | Each carer's location (for "who's nearest"), the person's home and away, the buttons on alerts, and the dashboard from anywhere | Home Assistant Cloud |
| **Admin access** | You, or an AI assistant on your computer, fixing and tuning the hub over SSH | Tailscale and the Terminal & SSH add-on |

Set both up **at your own home, before the hub moves**, and test them from another network (see the last section).

## What works without remote access

| | Without remote access |
|---|---|
| Alerts arriving on carers' phones | Works. Notifications go through Apple's and Google's push services, so the hub only needs internet |
| Carers' locations and "who's nearest" | Stops: a phone away from the house cannot report its location to the hub |
| The person's home and away | Stops, for the same reason |
| Buttons on alerts | Do not work away from the house: the phone has to reach the hub |
| Dashboard from your home | No |
| Fixing or tuning the hub, including stage 6 of the [full setup prompt](../../prompts/full-setup.md) | Only in person |

## Carers' phones: choose one

**1. Home Assistant Cloud (recommended).** A monthly subscription run by Nabu Casa, the company that funds Home Assistant's development. Current price: [nabucasa.com](https://www.nabucasa.com). Sign up under Settings, Home Assistant Cloud. Carers' phones then reach the hub from anywhere with nothing extra installed, and nothing on the router changes. Haiven's stored activity data stays on the hub, but the phones' connection, including location updates, passes through Nabu Casa's servers. Read their privacy terms before you sign up.

**2. Tailscale on every phone (free).** Each carer installs Tailscale and keeps it running. It works, but when Tailscale is off on one phone, that carer's location stops updating without anyone noticing, and "who's nearest" goes wrong. Not recommended for carers.

**3. Your own domain and a reverse proxy.** Free apart from the domain, but the hub is then reachable from the internet. Only for people who already run one and keep it patched. Not recommended for this use.

Whichever you choose, set each carer's Home Assistant app to use it, then turn off Wi-Fi on their phone and check the app still connects.

## Admin access: Tailscale and SSH

Tailscale makes a private network between your computer and the hub. Nothing is opened on the person's router, and it keeps working if they change broadband provider. The personal plan is free: [tailscale.com/pricing](https://tailscale.com/pricing).

1. **Tailscale on the hub.** Settings, Add-ons, Add-on store, Tailscale. Install, start it, open its web page and sign in with your Tailscale account.
2. **Tailscale on your computer.** Install it from tailscale.com and sign in with the same account. In the Tailscale admin page, note the hub's name (for example `homeassistant`).
3. **Terminal & SSH add-on on the hub.** Settings, Add-ons, Add-on store, Terminal & SSH. In its Configuration tab:
   - paste your computer's **public** SSH key into `authorized_keys` (on your computer: `ssh-keygen -t ed25519` if you have none, then copy the contents of `~/.ssh/id_ed25519.pub`);
   - leave `password` empty, so only your key can log in;
   - in the Network section, set the SSH port (22 is usual).
   Start the add-on.
4. **Test from your computer:** `ssh root@homeassistant` (use the hub's Tailscale name). Then run `ha core info`. If it answers, the AI assistant on your computer can use the same command.

Rules:
- Never forward a port on the router to the hub, for SSH or for port 8123.
- Never put a password on the SSH add-on instead of a key.
- Only people who help run the hub get Tailscale access. Remove a person from the Tailscale admin page when they stop helping, and remove their key from `authorized_keys`.
- An AI assistant uses your SSH key on your computer. It must never be given the key itself, and the key never goes into a file in git.

## Before the hub moves: the away test

On your own home network everything looks fine, so test from somewhere else:

1. Put your computer on your phone's hotspot. Run `ssh root@homeassistant` and `ha core info`.
2. On a carer's phone with Wi-Fi off, open the Home Assistant app, and check the dashboard loads and the carer's location has updated in Settings, People.
3. Send a test alert and tap its button with Wi-Fi off.

Write down the result. If any step fails, fix it before the hub goes to their house: fixing it there means a trip.
