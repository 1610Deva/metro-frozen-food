import { Link, Route, Routes } from "react-router";

function Home() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-20">
      <span className="text-sm font-semibold text-blue-600">
        METRO FROZEN FOOD
      </span>

      <h1 className="mt-4 text-4xl font-bold text-slate-900">
        Frontend Initialization
      </h1>

      <p className="mt-4 text-slate-600">
        React, Tailwind CSS, and React Router are ready.
      </p>

      <Link
        to="/catalog"
        className="mt-8 inline-block rounded-lg bg-blue-600 px-5 py-3 font-medium text-white hover:bg-blue-700"
      >
        Open Catalog
      </Link>
    </div>
  );
}

function Catalog() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-20">
      <h1 className="text-3xl font-bold text-slate-900">Product Catalog</h1>

      <p className="mt-4 text-slate-600">
        Catalog route is working successfully.
      </p>

      <Link to="/" className="mt-6 inline-block text-blue-600 hover:underline">
        Back to Home
      </Link>
    </div>
  );
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/catalog" element={<Catalog />} />
    </Routes>
  );
}

export default App;
