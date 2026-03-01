# Deployment Guide

Complete guide to deploying your SaaS boilerplate to production.

---

## Quick Deploy Options

### Option 1: Separate Hosting (Recommended)
- **Backend:** Railway, Render, or Heroku
- **Frontend:** Vercel or Netlify
- **Pros:** Easy, scalable, free tiers available
- **Cons:** Two deployments to manage

### Option 2: Single Server
- **Full Stack:** DigitalOcean, AWS, or your VPS
- **Pros:** Everything in one place
- **Cons:** More setup, manual SSL/scaling

---

## Option 1: Railway + Vercel (Easiest)

### Deploy Backend to Railway

1. **Create Railway account:** https://railway.app

2. **New Project:**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Connect your backend repo

3. **Configure:**
   - Add environment variables from `.env`:
     ```
     STRIPE_SECRET_KEY=sk_live_...
     MAILERLITE_API_KEY=...
     AUTH0_DOMAIN=...
     AUTH0_CLIENT_ID=...
     AUTH0_CLIENT_SECRET=...
     GA4_MEASUREMENT_ID=...
     GA4_API_SECRET=...
     ```

4. **Deploy:**
   - Railway auto-deploys on push
   - Get your backend URL: `https://your-app.railway.app`

### Deploy Frontend to Vercel

1. **Create Vercel account:** https://vercel.com

2. **New Project:**
   - Click "Add New" → "Project"
   - Import your frontend repo

3. **Configure:**
   - Framework: Create React App
   - Build command: `npm run build`
   - Output directory: `build`
   - Environment variables:
     ```
     REACT_APP_API_URL=https://your-app.railway.app/api
     REACT_APP_AUTH0_DOMAIN=your-tenant.auth0.com
     REACT_APP_AUTH0_CLIENT_ID=...
     ```

4. **Deploy:**
   - Vercel auto-deploys on push
   - Get your URL: `https://your-business.vercel.app`

5. **Custom Domain:**
   - Add your domain in Vercel settings
   - Update DNS records (Vercel provides instructions)

---

## Option 2: Render (Backend + Frontend)

### Backend

1. **Create account:** https://render.com

2. **New Web Service:**
   - Connect GitHub repo
   - Environment: Python 3
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

3. **Environment variables:** Add all from `.env`

4. **Deploy:** Auto-deploys on push

### Frontend

1. **New Static Site:**
   - Connect GitHub repo
   - Build command: `npm run build`
   - Publish directory: `build`

2. **Environment variables:** Add React env vars

3. **Deploy:** Auto-deploys on push

---

## Option 3: DigitalOcean (Single Droplet)

### 1. Create Droplet

- **Size:** $12/month (2GB RAM) minimum
- **OS:** Ubuntu 22.04
- **SSH Key:** Add your public key

### 2. Initial Server Setup

```bash
# SSH into server
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3 python3-pip nodejs npm nginx certbot python3-certbot-nginx

# Create app user
adduser --disabled-password --gecos "" appuser
```

### 3. Deploy Backend

```bash
# Switch to app user
su - appuser

# Clone repo
git clone https://github.com/yourusername/your-backend.git
cd your-backend

# Install dependencies
pip3 install -r requirements.txt

# Set up systemd service (as root)
exit
nano /etc/systemd/system/backend.service
```

**backend.service:**
```ini
[Unit]
Description=FastAPI Backend
After=network.target

[Service]
User=appuser
WorkingDirectory=/home/appuser/your-backend
Environment="PATH=/home/appuser/.local/bin"
ExecStart=/home/appuser/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Start service
systemctl start backend
systemctl enable backend
systemctl status backend
```

### 4. Deploy Frontend

```bash
# As app user
su - appuser
git clone https://github.com/yourusername/your-frontend.git
cd your-frontend

# Build
npm install
npm run build

# Copy to web root
exit
cp -r /home/appuser/your-frontend/build/* /var/www/html/
```

### 5. Configure Nginx

```bash
nano /etc/nginx/sites-available/default
```

**Nginx config:**
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Frontend
    location / {
        root /var/www/html;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Test and reload
nginx -t
systemctl reload nginx
```

### 6. SSL Certificate

```bash
certbot --nginx -d yourdomain.com
```

---

## Environment Variables

### Backend (.env)
```bash
# Required
STRIPE_SECRET_KEY=sk_live_...
MAILERLITE_API_KEY=...
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=...
AUTH0_CLIENT_SECRET=...
GA4_MEASUREMENT_ID=G-...
GA4_API_SECRET=...

# Optional
STRIPE_WEBHOOK_SECRET=whsec_...
GITHUB_TOKEN=...
ENVIRONMENT=production
```

### Frontend (.env.production)
```bash
REACT_APP_API_URL=https://api.yourdomain.com/api
REACT_APP_AUTH0_DOMAIN=your-tenant.auth0.com
REACT_APP_AUTH0_CLIENT_ID=...
```

---

## Post-Deployment Checklist

### DNS Configuration
- [ ] Point domain to hosting provider
- [ ] Add SSL certificate
- [ ] Test HTTPS works

### Auth0 Configuration
- [ ] Add production callback URLs
- [ ] Add production logout URLs
- [ ] Add production web origins

### Stripe Configuration
- [ ] Switch to live API keys
- [ ] Configure webhook endpoint
- [ ] Test checkout flow

### Analytics
- [ ] Verify GA4 tracking works
- [ ] Check DebugView for events

### Testing
- [ ] Test signup flow
- [ ] Test login flow
- [ ] Test subscription purchase
- [ ] Test contact form
- [ ] Test all pages load

---

## Monitoring

### Backend Health
```bash
# Check service status
systemctl status backend

# View logs
journalctl -u backend -f
```

### Frontend
- Check Vercel/Netlify dashboard
- Monitor Core Web Vitals

### Database (if added later)
- Set up backups
- Monitor connections

---

## Updating

### Railway/Vercel (auto-deploy)
```bash
git push origin main
# Automatically deploys
```

### Manual server
```bash
ssh appuser@your-server

# Backend
cd your-backend
git pull
systemctl restart backend

# Frontend
cd your-frontend
git pull
npm run build
sudo cp -r build/* /var/www/html/
```

---

## Scaling

### When to Scale

**Backend:**
- CPU > 70% consistently
- Response time > 500ms
- Memory > 80%

**Frontend:**
- Many concurrent users (Vercel/Netlify auto-scale)

### How to Scale

**Railway:**
- Increase instance size in dashboard
- Add replicas (Pro plan)

**DigitalOcean:**
- Resize droplet
- Add load balancer + multiple droplets

---

## Troubleshooting

### Backend won't start
```bash
# Check logs
journalctl -u backend -n 50

# Common issues:
# - Missing env vars
# - Port already in use
# - Dependencies not installed
```

### Frontend shows API errors
- Check CORS configuration
- Verify REACT_APP_API_URL is correct
- Check backend is running

### Stripe webhooks not working
- Verify webhook endpoint in Stripe dashboard
- Check webhook secret matches .env
- Test with Stripe CLI: `stripe listen --forward-to localhost:8000/api/webhooks/stripe`

---

## Costs

### Minimal Setup (Railway + Vercel)
- Railway: $0-5/month (free tier)
- Vercel: $0/month (free tier)
- **Total: ~$5/month**

### Production Setup
- Railway: $20/month (Pro)
- Vercel: $20/month (Pro) or free
- Domain: $12/year
- **Total: ~$40/month + domain**

### Self-Hosted (DigitalOcean)
- Droplet: $12-24/month
- Backups: $2-5/month
- Domain: $12/year
- **Total: ~$15-30/month + domain**

---

## Next Steps

1. Choose deployment option
2. Set up hosting accounts
3. Deploy backend
4. Deploy frontend
5. Configure DNS
6. Test everything
7. Go live! 🚀
