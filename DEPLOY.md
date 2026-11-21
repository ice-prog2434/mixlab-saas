# Mise en ligne (VPS + Docker + HTTPS automatique)

1. Prends un nom de domaine et un VPS Ubuntu (2 Go RAM minimum, 20 Go de disque ou plus).
2. Pointe le domaine vers l'IP du VPS (enregistrement DNS de type A).
3. Sur le VPS : `curl -fsSL https://get.docker.com | sh`
4. Envoie le dossier `mixlab` sur le VPS (scp ou git), puis :
   ```
   cd mixlab && cp .env.example .env && nano .env
   ```
   Remplis DOMAIN, DB_PASSWORD, SECRET_KEY (longue chaîne aléatoire) et les clés Stripe.
5. `docker compose up -d --build` puis ouvre https://ton-domaine (le certificat HTTPS est automatique).
6. Stripe : crée le produit à 30,99 €/mois, mets le price_... dans STRIPE_PRICE_ID, puis ajoute le webhook
   https://ton-domaine/billing/webhook (événements customer.subscription.created / updated / deleted)
   et copie son secret dans STRIPE_WEBHOOK_SECRET. Relance : `docker compose up -d`.
7. Teste en mode test Stripe (carte 4242 4242 4242 4242) avant de passer en clés live.
8. Sauvegarde les volumes (base + fichiers) régulièrement.

## PayPal (abonnement 30,99 €/mois)
1. developer.paypal.com > Apps & Credentials : crée une app (Sandbox d'abord) et copie le Client ID et le Secret dans `PAYPAL_CLIENT_ID` et `PAYPAL_SECRET`.
2. Crée le plan d'abonnement : 30,99 EUR, mensuel (dans ton compte PayPal Business, Produits et plans / Abonnements, ou via l'API). Copie l'identifiant `P-...` dans `PAYPAL_PLAN_ID`.
3. Dans l'app, ajoute le webhook `https://ton-domaine/billing/paypal/webhook` avec les événements `BILLING.SUBSCRIPTION.*`, puis copie le Webhook ID dans `PAYPAL_WEBHOOK_ID`.
4. `PAYPAL_ENV=sandbox` pour tester avec un compte acheteur sandbox, puis `live` avec les clés live (recrée plan et webhook en live).
5. `docker compose up -d` pour recharger la config.

Vérifie dans ton compte PayPal que ton pays permet bien de recevoir des paiements ET de retirer l'argent vers une banque. Selon les sources, ce n'est pas clair pour le Cameroun.
Si l'abonné annule chez PayPal, son accès s'arrête (pas de période de grâce).

## E-mails (mot de passe oublié)
Renseigne SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM (Brevo, Mailjet, Gmail avec mot de passe d'application...). Sans SMTP, le lien de réinitialisation s'affiche seulement dans les logs : `docker compose logs app`.

## Mise à jour d'une base existante
Les nouvelles colonnes (PayPal) ne sont pas ajoutées automatiquement à une base déjà créée. Si tu as déjà déployé la version précédente, soit tu repars d'une base vide, soit tu ajoutes les colonnes `paypal_subscription_id` et `sub_provider` à la table `users` à la main.
