import { Link } from 'react-router-dom';
import useConfig from '../hooks/useConfig';

function Footer() {
  const config = useConfig();
  const { footer, branding } = config;

  return (
    <footer className="bg-gray-900 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
          {footer.columns.map((column, i) => (
            <div key={i}>
              <h3 className="font-semibold text-lg mb-4">{column.title}</h3>
              <ul className="space-y-2">
                {column.links.map((link, j) => (
                  <li key={j}>
                    {link.url.startsWith('http') ? (
                      <a 
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-gray-400 hover:text-white"
                      >
                        {link.label}
                      </a>
                    ) : (
                      <Link 
                        to={link.url}
                        className="text-gray-400 hover:text-white"
                      >
                        {link.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="border-t border-gray-800 pt-8 flex flex-col md:flex-row justify-between items-center">
          <p className="text-gray-400 text-sm">{footer.copyright}</p>
          <p className="text-gray-400 text-sm mt-4 md:mt-0">{footer.tagline}</p>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
