import { useState } from 'react';
import useConfig from '../hooks/useConfig';

function FAQ() {
  const config = useConfig();
  const { faq } = config;
  const [openIndex, setOpenIndex] = useState(null);

  return (
    <div className="min-h-screen py-20 px-4">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-5xl font-bold text-center mb-4">{faq.headline}</h1>
        <p className="text-xl text-gray-600 text-center mb-16">Find answers to common questions</p>

        {faq.categories.map((category, catIndex) => (
          <div key={catIndex} className="mb-12">
            <h2 className="text-2xl font-bold mb-6">{category.name}</h2>
            <div className="space-y-4">
              {category.questions.map((item, qIndex) => {
                const index = `${catIndex}-${qIndex}`;
                const isOpen = openIndex === index;
                
                return (
                  <div key={qIndex} className="bg-white rounded-lg shadow">
                    <button
                      onClick={() => setOpenIndex(isOpen ? null : index)}
                      className="w-full p-6 text-left flex justify-between items-center"
                    >
                      <h3 className="font-semibold text-lg pr-4">{item.question}</h3>
                      <span className="text-2xl flex-shrink-0">{isOpen ? '−' : '+'}</span>
                    </button>
                    {isOpen && (
                      <div className="px-6 pb-6">
                        <p className="text-gray-600">{item.answer}</p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default FAQ;
