const os = require("os");
const fs = require("fs");
const url = require("url");
const http = require("http");
const crypto = require("crypto");
const request = require("request");

const AUTH0ֹֹֹֹֹ_DOMAIN = "syncninja.eu.auth0.com";
const AUTH0_CLIENT_ID = "vHU0FyOXfEbsL7zZ1WVTzBmrfEYw6aHd";

function base64URLEncode(str) {
  return str.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
}

function sha256(buffer) {
  return crypto.createHash("sha256").update(buffer).digest();
}

var verifier = base64URLEncode(crypto.randomBytes(32));
var challenge = base64URLEncode(sha256(verifier));

function getAuthenticationUrl(codeChallenge, state) {
  return [
    `https://${AUTH0ֹֹֹֹֹ_DOMAIN}/authorize`,
    `?response_type=code`,
    `&code_challenge=${codeChallenge}`,
    `&code_challenge_method=S256`,
    `&client_id=${AUTH0_CLIENT_ID}`,
    `&redirect_uri=http://localhost:3000/callback`,
    `&scope=openid%20email%20profile`,
    `&audience=cliapi_publish`,
    `&state=${state}`
  ].join("");
}

function authenticateAndGetAccessCode(challenge) {
  console.log(" ");
  console.log("In order to login, please browse to the following page: ");
  console.log(getAuthenticationUrl(challenge, "xyzABC123"));

  return new Promise((resolve, reject) => {
    function handleAuth0Response(req, res) {
      const urlQuery = url.parse(req.url, true).query;
      const { code, state, error, error_description } = urlQuery;

      // this validation was simplified for the example
      if (code && state) {
        // Obtain Token
        // getToken(verifier, code);
        res.writeHead(302, {
          Location: "https://sync.ninja/?login=success"
        });
        resolve(code);
      } else {
        res.writeHead(302, {
          Location: "https://sync.ninja/?login=error"
        });

        reject();
      }

      res.end();
    }

    const server = http.createServer(handleAuth0Response).listen(3000, err => {
      if (err) {
        console.log(`Unable to start an HTTP server on port ${this.config.port}.`, err);
      }
    });
  });
}

function getToken(codeVerifier, code) {
  const requestParams = {
    url: `https://${AUTH0ֹֹֹֹֹ_DOMAIN}/oauth/token`,
    headers: { "content-type": "application/x-www-form-urlencoded" },
    form: {
      grant_type: "authorization_code",
      client_id: AUTH0_CLIENT_ID,
      code_verifier: codeVerifier,
      code,
      // scope: "openid profile email offline_access",
      redirect_uri: `http://localhost:3000/xx`
    }
  };

  return new Promise((resolve, reject) => {
    request.post(requestParams, (err, response, body) => {
      if (err || response.statusCode !== 200) {
        console.log("Failed to get an access token.", err);
        reject();
      }

      // validations removed for simplicity
      const data = JSON.parse(body);
      resolve(data);
    });
  });
}

async function getUserInfo(token) {
  const requestParams = {
    url: `https://${AUTH0ֹֹֹֹֹ_DOMAIN}/userinfo`,
    headers: { Authorization: `Bearer ${token}` }
  };

  return new Promise((resolve, reject) => {
    request.get(requestParams, (err, response, body) => {
      console.log(response.statusCode);
      if (err || response.statusCode !== 200) {
        console.log("Failed to get user info.", err);
        reject();
      }

      const data = JSON.parse(body);
      resolve(data);
    });
  });
}

function saveToken(token) {
  const path = `${os.homedir()}/.ninja`;

  try {
    fs.mkdirSync(path);
  } catch (error) {}

  fs.writeFileSync(
    `${path}/config.json`,
    JSON.stringify({
      status: "loggedIn",
      token: token
    })
  );
}

async function main() {
  const code = await authenticateAndGetAccessCode(challenge);
  const token = await getToken(verifier, code);
  const userInfo = await getUserInfo(token.access_token);
  saveToken({
    token,
    userInfo
  });

  process.exit(0);
}
main();
