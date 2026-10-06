import React from 'react';

export default function TestComponent() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
        <h1 className="text-2xl font-bold text-center text-gray-900 mb-4">
          Expenzaro Frontend Test
        </h1>
        <p className="text-center text-gray-600 mb-6">
          If you can see this, the basic React setup is working!
        </p>
        <div className="space-y-2 text-sm text-gray-500">
          <p>✅ React is rendering</p>
          <p>✅ Tailwind CSS is working</p>
          <p>✅ Vite dev server is running</p>
        </div>
        <div className="mt-6 text-center">
          <a 
            href="/login" 
            className="text-blue-600 hover:text-blue-800 underline"
          >
            Go to Login Page
          </a>
        </div>
      </div>
    </div>
  );
}