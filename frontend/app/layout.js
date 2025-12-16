import "./global.css";

export const metadata = {
  title: "Ag Science Exam Generator | AI-Powered",
  description: "Generate authentic Leaving Cert Agricultural Science exam questions with AI",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <script src="https://cdn.tailwindcss.com"></script>
      </head>
      <body className="antialiased">{children}</body>
    </html>
  );
}