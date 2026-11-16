// Thin wrapper around fetch() for the REST API.

const TOKEN_KEY = "cinema_token";

class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

const Api = {
  getToken() {
    return localStorage.getItem(TOKEN_KEY);
  },
  setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
  },
  clearToken() {
    localStorage.removeItem(TOKEN_KEY);
  },
  isLoggedIn() {
    return Boolean(this.getToken());
  },

  async request(method, path, body) {
    const headers = {};
    const token = this.getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const options = { method, headers };
    if (body instanceof FormData) {
      options.body = body; // the browser sets the multipart Content-Type itself
    } else if (body !== undefined) {
      headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }

    const response = await fetch(path, options);
    if (response.status === 401 && token) this.clearToken(); // token expired

    if (!response.ok) {
      let message = `Request failed (${response.status})`;
      try {
        const data = await response.json();
        if (typeof data.detail === "string") message = data.detail;
        else if (Array.isArray(data.detail)) message = data.detail.map((d) => d.msg).join("; ");
      } catch {
        // response had no JSON body
      }
      throw new ApiError(response.status, message);
    }
    return response.status === 204 ? null : response.json();
  },

  get(path) {
    return this.request("GET", path);
  },
  post(path, body) {
    return this.request("POST", path, body);
  },
  put(path, body) {
    return this.request("PUT", path, body);
  },
  delete(path) {
    return this.request("DELETE", path);
  },
};