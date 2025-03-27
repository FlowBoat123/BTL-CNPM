import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import { getFirestore, collection, getDocs, addDoc } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js";

// Cấu hình Firebase

const firebaseConfig = {
  apiKey: "AIzaSyC7hvIFkHETCdA6YdxdtD6egFcG5m-Eo4o",
  authDomain: "clinic-management-6d798.firebaseapp.com",
  projectId: "clinic-management-6d798",
  storageBucket: "clinic-management-6d798.firebasestorage.app",
  messagingSenderId: "488411431084",
  appId: "1:488411431084:web:d9d39a4b43992083509f09",
  measurementId: "G-Z0KQ8J00C3"
};

// Khởi tạo Firebase
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

export { db };