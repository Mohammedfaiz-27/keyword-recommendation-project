import React from 'react';

function EntitiesDisplay({ entities }) {
  if (!entities) {
    return (
      <div className="text-center py-8 text-gray-500">
        No entities extracted
      </div>
    );
  }

  const entityTypes = [
    {
      key: 'persons',
      label: 'People',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
      ),
      color: 'blue',
    },
    {
      key: 'organizations',
      label: 'Organizations',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
        </svg>
      ),
      color: 'purple',
    },
    {
      key: 'locations',
      label: 'Locations',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      ),
      color: 'green',
    },
    {
      key: 'dates',
      label: 'Dates',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      ),
      color: 'orange',
    },
  ];

  const colorClasses = {
    blue: {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      icon: 'text-blue-500',
      tag: 'bg-blue-100 text-blue-700',
    },
    purple: {
      bg: 'bg-purple-50',
      border: 'border-purple-200',
      icon: 'text-purple-500',
      tag: 'bg-purple-100 text-purple-700',
    },
    green: {
      bg: 'bg-green-50',
      border: 'border-green-200',
      icon: 'text-green-500',
      tag: 'bg-green-100 text-green-700',
    },
    orange: {
      bg: 'bg-orange-50',
      border: 'border-orange-200',
      icon: 'text-orange-500',
      tag: 'bg-orange-100 text-orange-700',
    },
  };

  const hasAnyEntities = entityTypes.some(
    (type) => entities[type.key] && entities[type.key].length > 0
  );

  if (!hasAnyEntities) {
    return (
      <div className="text-center py-8 text-gray-500">
        No named entities found in the content
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {entityTypes.map((type) => {
        const items = entities[type.key] || [];
        if (items.length === 0) return null;

        const colors = colorClasses[type.color];

        return (
          <div
            key={type.key}
            className={`${colors.bg} border ${colors.border} rounded-lg p-4`}
          >
            <div className="flex items-center mb-3">
              <span className={colors.icon}>{type.icon}</span>
              <h3 className="ml-2 font-medium text-gray-900">{type.label}</h3>
              <span className={`ml-auto text-xs px-2 py-0.5 rounded-full ${colors.tag}`}>
                {items.length}
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {items.map((item, index) => (
                <span
                  key={index}
                  className={`text-sm px-2 py-1 rounded ${colors.tag}`}
                >
                  {item}
                </span>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default EntitiesDisplay;
