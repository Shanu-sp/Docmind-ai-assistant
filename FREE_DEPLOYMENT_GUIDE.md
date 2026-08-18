# DocMind — 100% Free Production Deployment Guide

This guide provides a step-by-step deployment procedure to host **DocMind** on the web **100% FREE** with **zero subscription or credit card required**.

---

## 🏆 Chosen 100% Free Technology Stack

| Layer | Chosen Platform | Why It's The Best Choice |
| :--- | :--- | :--- |
| **Frontend** | **Vercel** | Industry standard for React/Vite, instant GitHub deployments, fast CDN. |
| **Backend** | **Render** | Native Python/Django web service support, automated SSL, free tier. |
| **Database & Files**| **Supabase** | Managed PostgreSQL DB + 1 GB File Storage bucket in one dashboard (0 credit card). |
| **Authentication** | **Google Cloud Console** | Official Google OAuth 2.0 Single Sign-On (100% free unlimited logins). |
| **AI LLM Engine** | **Google AI Studio** | Gemini 2.5 Flash API key (Free tier). |

---

## 📋 Step 1: Set Up Free Database & File Storage (Supabase)

1. **Create Account**:
   - Go to [Supabase.com](https://supabase.com/) and sign up with GitHub or Google.
2. **Create New Project**:
   - Click **New Project**, name it `docmind-db`, and set a database password.
   - Choose a region close to you and select the **Free Tier**.
3. **Get Database Connection String**:
   - In Supabase Settings -> **Database** -> **Connection string**, copy the `URI` string (`postgresql://postgres:[PASSWORD]@db.xxxx.supabase.co:5432/postgres`).
4. **Create Document Storage Bucket**:
   - Go to **Storage** -> **Buckets** -> Click **New Bucket**.
   - Name: `documents`.
   - Toggle **Public Bucket** to `ON`.
   - Click **Save**.

---

## 📋 Step 2: Publish Google OAuth (Google Cloud Console)

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Select your `DocMind AI` project.
3. Go to **APIs & Services** -> **OAuth consent screen**.
4. Click **Publish App** (moves status from *Testing* to *In Production*).
5. Under **Authorized Domains**, add `vercel.app` and `onrender.com`.

---

## 📋 Step 3: Deploy Django Backend for Free (Render)

1. **Push Code to GitHub**:
   - Push your `Chatbot project` repository to GitHub.
2. **Create Web Service on Render**:
   - Go to [Render.com](https://render.com/) and sign up.
   - Click **New +** -> **Web Service** -> Connect your GitHub repository.
3. **Configure Service Settings**:
   - **Name**: `docmind-backend`
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt && python manage.py migrate`
   - **Start Command**: `gunicorn docmind_backend.wsgi:application`
   - **Instance Type**: `Free`
4. **Add Environment Variables**:
   Under **Environment**, add:
   - `DEBUG`: `False`
   - `SECRET_KEY`: `(Generate any long random string)`
   - `GEMINI_API_KEY`: `(Your Gemini API Key)`
   - `GOOGLE_CLIENT_ID`: `303095572158-lasdg9d2l7b9phdld1rajhs2sa851f93.apps.googleusercontent.com`
   - `DATABASE_URL`: `(Your Supabase Postgres URI from Step 1)`
5. Click **Create Web Service**. Copy your backend URL:
   - **Live Backend URL**: `https://docmind-ai-assistant-backend.onrender.com`

---

## 📋 Step 4: Deploy React Frontend for Free (Vercel)

1. **Create Project on Vercel**:
   - Go to [Vercel.com](https://vercel.com/) and sign in with GitHub.
   - Click **Add New...** -> **Project** -> Import `Shanu-sp/Docmind-ai-assistant`.
2. **Configure Frontend Build Settings**:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
3. **Add Environment Variables**:
   Under **Environment Variables**, add:
   - `VITE_API_BASE_URL`: `https://docmind-ai-assistant-backend.onrender.com/api`
   - `VITE_GOOGLE_CLIENT_ID`: `303095572158-3thj1a4q36a78dq3tfdnn336nhjdrjlf.apps.googleusercontent.com`
4. Click **Deploy**.
5. Copy your live website URL (e.g., `https://docmind-ai-assistant.vercel.app`).

---

## 📋 Step 5: Update OAuth & CORS URLs

1. **Update Google OAuth Credentials**:
   - In Google Cloud Console -> **Credentials** -> Edit your OAuth Client (`303095572158-3thj1a4q36a78dq3tfdnn336nhjdrjlf`).
   - Under **Authorized JavaScript Origins**, add your Vercel URL (e.g., `https://docmind-ai-assistant.vercel.app`).
   - Click **Save**.

---

## 🎉 Verification Checklist

- [x] Supabase Postgres connected (via Connection Pooler).
- [x] Render Django backend active & SSL secure: `https://docmind-ai-assistant-backend.onrender.com`.
- [ ] Vercel React frontend live on custom `.vercel.app` domain.
- [ ] Google OAuth sign-in functional for all external users.

