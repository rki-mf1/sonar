# Sonar Frontend

A web frontend to the sonar mutation database.

# Setup

```bash
git clone https://github.com/rki-mf1/sonar.git
cd sonar/apps/frontend
```

Make sure you have npm installed (`conda create -n sonar-frontend nodejs` will work with conda), and then follow the frontend docs:

```
$ npm install
```

Next you probably want to customize the url of the sonar backend. For local
builds you can still set this from `sonar/apps/frontend/.env.production` or
directly from the command line when building the frontend:

```
$ VITE_SONAR_BACKEND_ADDRESS=https://myserver.com/api/ npm run build
```

Then copy the built files into the backend `work/` directory. You might need to tweak the commands below depending on the relative location of sonar-frontend and sonar-backend, and whether you are updating an existing copy of the frontend or doing this for the first time:

```
$ npm run build:backend-proxy
```

Now you should be able to access the frontend on your server at port 443 (e.g. `https://servername.org`).

## Project Setup

```sh
npm install
```

### Compile and Hot-Reload for Development

```sh
npm run dev
```

Note: the url of the backend api (`VITE_SONAR_BACKEND_ADDRESS`) is set in the `.env.development` file. It defaults to "http://localhost:8000/api/".

This local dev flow is unchanged and still provides automatic updates via the
Vite dev server.

### Type-Check, Compile and Minify for Production

First, set the url of the backend api (`VITE_SONAR_BACKEND_ADDRESS`) in a file
`.env.production` or `.env.production.local` if you do not want to add the url
to git. Next, run:

```sh
npm run build
```

Output files will be placed in the `./dist/` folder.

## Deploying the prebuilt frontend image

The published frontend image is `ghcr.io/rki-mf1/sonar-frontend`.

Unlike the static Vite build, the prebuilt container reads its deployment
settings at container startup. Use:

- `SONAR_FRONTEND_BACKEND_ADDRESS` to point the app at the backend API
- `SONAR_FRONTEND_AUTH_TOKEN` only if you explicitly want to inject a token

For a full image-based deployment example, see
[`example-deploy`](../../example-deploy).
