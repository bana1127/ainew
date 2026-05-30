export function Header() {
  return (
    <header className="sticky top-0 z-10 border-b border-line bg-white/95 backdrop-blur">
      <div className="flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
        <div>
          <p className="text-xs font-medium uppercase text-gray-500">
            Operations
          </p>
          <p className="text-sm font-semibold text-ink">Admin Dashboard</p>
        </div>
        <div className="rounded-full border border-line bg-mist px-3 py-1 text-xs font-medium text-gray-600">
          Local Development
        </div>
      </div>
    </header>
  );
}
