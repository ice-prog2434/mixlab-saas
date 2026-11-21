# MixLab AI — backend (phase 2-3)

FastAPI + FFmpeg. Inscription, essai gratuit 7 jours, abonnement Stripe 30,99 €/mois, mixage voix + instru.

## Installation
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # puis remplis SECRET_KEY (et Stripe)
# FFmpeg 4.4+ requis (ffmpeg -version)
export $(grep -v '^#' .env | xargs)
uvicorn app.main:app --reload
```
Docs interactives : http://localhost:8000/docs — Tests : `pytest`

## Stripe
1. Crée un produit « MixLab AI » à 30,99 € / mois en EUR, copie le `price_...` dans `STRIPE_PRICE_ID`.
2. `STRIPE_SECRET_KEY` = clé secrète (mode test d'abord).
3. Webhook vers `/billing/webhook` (événements `customer.subscription.*`), copie le secret dans `STRIPE_WEBHOOK_SECRET`.
Test local : `stripe listen --forward-to localhost:8000/billing/webhook`.

## Essai gratuit
7 jours à l'inscription, sans carte (`TRIAL_DAYS`). Après : accès seulement si l'abonnement est `active`/`trialing`.

## Paiements
Stripe (carte) et PayPal (abonnement). Voir DEPLOY.md. Mot de passe oublié par e-mail (SMTP). Limitation de débit sur /auth (en mémoire, 1 processus).

## Pas encore fait (honnêtement)
Espace admin, stockage S3, file de tâches (Celery/RQ à la place de BackgroundTasks), migrations Alembic, réduction de bruit, correction de hauteur. Le frontend React se branche sur ces routes.
