import { NavLink } from "react-router-dom";

const UnderConstruction = ({ page }: { page: string }) => {
  return (
    <div className="bg-white">
      <main className="mx-auto w-full max-w-7xl px-6 pb-16 pt-10 sm:pb-24 lg:px-8">
        <img
          className="mx-auto h-20 w-auto sm:h-12"
          src="/logo.svg"
          alt="logo"
        />
        <div className="mx-auto mt-20 max-w-2xl text-center sm:mt-24">
          <p className="text-base font-semibold leading-8 text-blue-600">
            Under Construction
          </p>
          <h1 className="mt-4 text-3xl font-bold tracking-tight text-gray-900 sm:text-5xl">
            The {page} page is being built
          </h1>
          <p className="mt-4 text-base leading-7 text-gray-600 sm:mt-6 sm:text-lg sm:leading-8">
            Hang tight! We&apos;re working hard on this page. Check back soon
            for updates.
          </p>
        </div>
        <div className="mx-auto mt-16 text-center sm:mt-20">
          <NavLink
            to="/"
            className="text-base font-semibold leading-7 text-blue-600"
          >
            <span aria-hidden="true">&larr;</span> Back
          </NavLink>
        </div>
      </main>
    </div>
  );
};

export default UnderConstruction;
