import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api",
  timeout: 15000,
});

export function getErrorMessage(error, fallback = "Something went wrong. Please try again.") {
  if (error.response?.data?.detail) return error.response.data.detail;
  if (error.code === "ERR_NETWORK") {
    return "Cannot reach the API. Check that the backend is running at http://localhost:8000 and try again.";
  }
  return error.message || fallback;
}

export default api;
