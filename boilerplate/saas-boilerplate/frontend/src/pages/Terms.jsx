import useConfig from '../hooks/useConfig';

function Terms() {
  const config = useConfig();
  const { terms_of_service } = config;

  return (
    <div className="min-h-screen py-20 px-4">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-5xl font-bold mb-4">Terms of Service</h1>
        <p className="text-gray-600 mb-12">Last updated: {terms_of_service.last_updated}</p>

        <div className="prose max-w-none">
          {terms_of_service.sections.map((section, i) => (
            <div key={i} className="mb-8">
              <h2 className="text-2xl font-bold mb-4">{section.title}</h2>
              <p className="text-gray-700 whitespace-pre-line">{section.content}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default Terms;
