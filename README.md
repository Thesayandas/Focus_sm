# ⚡ NexusAuth // Google OAuth 2.0 & Phone Telephony Hub

A next-generation, high-aesthetic single-operation web application that demonstrates **Google OAuth 2.0 Identity Extraction** and **Seamless Post-OAuth Phone Number Binding**.

![NexusAuth Preview](https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1200&auto=format&fit=crop&q=80)

---

## 🌟 Key Features

1. **Eye-Catching Cyber-Neon & Aurora UI**:
   - Built with dynamic Canvas particle physics, glassmorphism blur effects, and ambient gradient glows.
   - Interactive **3D Tilt Holographic ID Card** responding to cursor physics.
   - Confetti bursts on successful OAuth verification and telephony synchronization.
   
2. **Single-Operation Workflow**:
   - **Step 1: Google OAuth 2.0 Authentication** — Retrieves permitted scopes (`openid`, `email`, `profile`).
   - **Step 2: Instant Phone Onboarding** — Smart international dial code picker (`+1`, `+91`, `+44`, etc.) and real-time formatting.
   - **Step 3: Verified Digital Passport & JSON Inspector** — Visualizes the unified identity payload with copyable JSON.

3. **Dual-Mode Engine**:
   - **Live Google OAuth Mode**: Plug in your Google Cloud credentials to run real OAuth 2.0 authentication.
   - **Instant Sandbox Mode**: Built-in 1-click test personas for zero-configuration instant demonstrations.

---

## 🚀 Quickstart on Kali Linux

### 1. Set Up Virtual Environment & Dependencies
```bash
# Navigate to project directory
cd focus_sm

# Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. (Optional) Configure Google Cloud Credentials
If you want to test with real Google accounts:
1. Open `.env`
2. Add your Google OAuth Client ID & Client Secret from Google Cloud Console:
   ```env
   GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   ```
*(If left blank, the app automatically runs in Instant Interactive Sandbox Mode)*

### 3. Launch the Application
```bash
python3 app.py
```

Open your browser and navigate to:
```text
http://127.0.0.1:5000
```

---

## 📁 Project Structure

```text
├── app.py                  # Flask backend with OAuth 2.0 client & REST endpoints
├── requirements.txt        # Flask, Authlib, requests, python-dotenv
├── .env                    # Environment variables & secrets
├── .env.example            # Template for environment configuration
├── templates/
│   └── index.html          # Cyber-neon single-operation interface with Canvas particles & 3D tilt
└── README.md               # Documentation & setup guide
```
