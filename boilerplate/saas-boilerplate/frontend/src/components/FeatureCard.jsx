function FeatureCard({ icon, title, description }) {
  return (
    <div className="text-center p-6 rounded-lg shadow-sm hover:shadow-md transition-shadow">
      <div className="text-4xl mb-4">{icon}</div>
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-gray-600">{description}</p>
    </div>
  );
}

export default FeatureCard;
