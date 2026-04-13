import "./global.css";

export const metadata = {
  title: "Ag Science Exam Generator | AI-Powered",
  description: "Generate authentic Leaving Cert Agricultural Science exam questions with AI",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      {/* Removed the head script tag entirely  to make webiste load faster*/}
      <body className="antialiased" suppressHydrationWarning>{children}</body>
    </html>
  );
}