# ui

The v0.3+ user interface.



## Summary & usage

A webapp built on [NuxtJS](https://github.com/nuxt/nuxt.js), based on [NuxtJS + CoreUI boilerplate](https://github.com/muhibbudins/nuxt-coreui), used as the front-end for a [Flask](https://github.com/pallets/flask) app served by [Waitress](https://github.com/Pylons/waitress).

In the `isimple` application the webapp is served locally, directly from compiled files. Therefore you shouldn’t need to worry about anything, hopefully.



## Development

#### Setup

1. Install [npm](https://www.npmjs.com/get-npm)

2. Navigate to this directory and install the dependencies

   ```bash
   cd ui/ && npm install
   ```

#### Compiling the frontend

1. (Set up)

2. Compile

   ```bash
   cd ui/ && npm run generate
   ```

The compiled files are stored in `ui/dist/`.

#### Running the frontend in development mode

1. (Set up)

2. Run the backend server (default address is http://localhost:7951)

	```
   (.venv) $ python .server.py
	```

3. Run the frontend development server (default address is http://localhost:3000)

   ```bash
   cd ui/ && npm run dev
   ```
   
   The development server [hot-reloads](https://vue-loader.vuejs.org/guide/hot-reload.html) content from the source code in `ui/` and proxies API calls to the backend server.