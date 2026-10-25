import axios from "axios";

const apiBaseUrl =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV ? "http://localhost:8000/api" : "/api");

const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 15000,
});

export function getErrorMessage(error, fallback = "Something went wrong. Please try again.") {
  if (error.response?.data?.detail) return error.response.data.detail;
  if (error.code === "ERR_NETWORK") {
    return import.meta.env.DEV
      ? "Cannot reach the API. Check that the backend is running at http://localhost:8000 and try again."
      : "Cannot reach the API. Check the deployment's VITE_API_URL setting and try again.";
  }
  return error.message || fallback;
}

export default api;
