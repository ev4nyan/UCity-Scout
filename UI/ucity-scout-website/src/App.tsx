import React, { useState, useEffect } from 'react';

// --- TypeScript Interfaces ---

interface PropertyIntelligence {
  opa_account_num: string;
  address: string;
  owner_name: string;
  landlord_locality: string;
  violation_count: number;
  open_violation_count: number;
  permit_count: number;
  has_rental_license: boolean;
  rental_license_active: boolean;
  is_owner_occupied: boolean;
  property_age: number;
  exterior_condition: string;
  interior_condition: string;
  bedrooms: number;
  bathrooms: number;
  livable_area: number;
  has_central_air: boolean;
  safety_score: number;
  maintenance_score: number;
  landlord_score: number;
  trustability_score: number;
  risk_level: string;
  risk_flags: string[];
  student_warnings: string[];
}

interface IconProps {
  className?: string;
}

// --- Icons ---

const SearchIcon: React.FC = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6 text-gray-400">
    <circle cx="11" cy="11" r="8"></circle>
    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
  </svg>
);

const CheckCircle: React.FC<IconProps> = ({ className }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
    <polyline points="22 4 12 14.01 9 11.01"></polyline>
  </svg>
);

const XCircle: React.FC<IconProps> = ({ className }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <circle cx="12" cy="12" r="10"></circle>
    <line x1="15" y1="9" x2="9" y2="15"></line>
    <line x1="9" y1="9" x2="15" y2="15"></line>
  </svg>
);

const AlertTriangle: React.FC<IconProps> = ({ className }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path>
    <line x1="12" y1="9" x2="12" y2="13"></line>
    <line x1="12" y1="17" x2="12.01" y2="17"></line>
  </svg>
);

const ShieldIcon: React.FC<IconProps> = ({ className }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
  </svg>
);

// --- Main App ---

export default function App() {
  const [opaInput, setOpaInput] = useState<string>('883325150');
  const [propertyData, setPropertyData] = useState<PropertyIntelligence | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!opaInput) {
      setError("Please enter an OPA account number");
      return;
    }

    setIsLoading(true);
    setError(null);
    setPropertyData(null);

    try {
      const response = await fetch(`http://127.0.0.1:5001/api/property/${opaInput}`);
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || "Property intelligence not found");
      }
      const data: PropertyIntelligence = await response.json();
      setPropertyData(data);
    } catch (err: any) {
      console.log(err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    handleSearch();
  }, []);

  return (
    <div className="bg-gray-100 min-h-screen font-sans">
      <header className="bg-white shadow-md">
        <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">
            <span className="text-blue-600">UC</span> Scout 🕵️‍♀️
          </h1>
          <div className="w-full max-w-md">
            <div className="relative flex items-center">
              <div className="absolute left-3 flex items-center pointer-events-none">
                <SearchIcon />
              </div>
              <input
                type="text"
                value={opaInput}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setOpaInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Enter OPA Account Number..."
                className="block w-full bg-gray-100 border border-gray-300 rounded-l-md py-2 pl-12 pr-3 leading-5 placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              />
              <button
                onClick={handleSearch}
                className="bg-blue-600 text-white px-4 py-2 rounded-r-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                Search
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {isLoading && <div className="text-center text-gray-500">Loading property intelligence...</div>}
        {error && <div className="text-center text-red-500 bg-red-100 p-4 rounded-md">{error}</div>}
        {propertyData && <PropertyReport data={propertyData} />}
      </main>
    </div>
  );
}

// --- Property Report Component ---

function PropertyReport({ data }: { data: PropertyIntelligence }) {
  const getRiskColor = (level: string) => {
    switch (level) {
      case 'LOW': return 'bg-green-100 text-green-800';
      case 'MODERATE': return 'bg-yellow-100 text-yellow-800';
      case 'HIGH': return 'bg-orange-100 text-orange-800';
      case 'CRITICAL': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 75) return 'text-green-600';
    if (score >= 50) return 'text-yellow-600';
    if (score >= 25) return 'text-orange-600';
    return 'text-red-600';
  };

  const getLocalityBadge = (locality: string) => {
    if (locality === 'LOCAL') return 'bg-green-100 text-green-800';
    if (locality === 'DISTANT') return 'bg-red-100 text-red-800';
    return 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="bg-white rounded-lg shadow-xl overflow-hidden">
      <div className="p-6 border-b bg-gradient-to-r from-blue-500 to-blue-600">
        <h2 className="text-3xl font-bold text-white">{data.address}</h2>
        <div className="flex items-center mt-2 space-x-4">
          <span className={`inline-block rounded-full px-3 py-1 text-sm font-semibold ${getRiskColor(data.risk_level)}`}>
            {data.risk_level} RISK
          </span>
          <span className={`inline-block rounded-full px-3 py-1 text-sm font-semibold ${getLocalityBadge(data.landlord_locality)}`}>
            {data.landlord_locality} LANDLORD
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-gray-200">
        <div className="col-span-2 bg-white">
          <div className="p-6 border-b">
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-semibold text-gray-800">Student Trustability Score</h3>
              <div className="text-5xl font-bold" style={{ color: data.trustability_score >= 75 ? '#10b981' : data.trustability_score >= 50 ? '#f59e0b' : '#ef4444' }}>
                {data.trustability_score}
              </div>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-4">
              <div className="text-center">
                <div className={`text-2xl font-bold ${getScoreColor(data.safety_score)}`}>{data.safety_score}</div>
                <div className="text-xs text-gray-500">Safety</div>
              </div>
              <div className="text-center">
                <div className={`text-2xl font-bold ${getScoreColor(data.maintenance_score)}`}>{data.maintenance_score}</div>
                <div className="text-xs text-gray-500">Maintenance</div>
              </div>
              <div className="text-center">
                <div className={`text-2xl font-bold ${getScoreColor(data.landlord_score)}`}>{data.landlord_score}</div>
                <div className="text-xs text-gray-500">Landlord</div>
              </div>
            </div>
          </div>

          <div className="p-6 border-b">
            <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mr-2 text-blue-600">
                <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>
              Ownership
            </h3>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-600">Owner:</span>
                <span className="font-semibold">{data.owner_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Owner Occupied:</span>
                <span className="font-semibold">{data.is_owner_occupied ? 'Yes ✓' : 'No'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Landlord Location:</span>
                <span className={`font-semibold ${data.landlord_locality === 'LOCAL' ? 'text-green-600' : data.landlord_locality === 'DISTANT' ? 'text-red-600' : 'text-gray-600'}`}>
                  {data.landlord_locality}
                </span>
              </div>
            </div>
          </div>

          <div className="p-6 border-b">
            <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
              <ShieldIcon className="h-5 w-5 mr-2 text-blue-600" />
              Code Compliance
            </h3>
            <div className="space-y-3">
              <div className={`flex items-start p-3 rounded-lg ${data.has_rental_license && data.rental_license_active ? 'bg-green-50' : 'bg-red-50'}`}>
                {data.has_rental_license && data.rental_license_active ? 
                  <CheckCircle className="h-6 w-6 text-green-500 mt-1 flex-shrink-0" /> : 
                  <XCircle className="h-6 w-6 text-red-500 mt-1 flex-shrink-0" />
                }
                <div className="ml-3">
                  <h4 className={`text-md font-semibold ${data.has_rental_license && data.rental_license_active ? 'text-green-800' : 'text-red-800'}`}>
                    Rental License
                  </h4>
                  <p className="text-sm text-gray-600">
                    {data.has_rental_license && data.rental_license_active ? 
                      'Active rental license on file' : 
                      data.has_rental_license ? 
                      'Rental license expired or inactive' : 
                      'No rental license found'}
                  </p>
                </div>
              </div>

              <div className={`flex items-start p-3 rounded-lg ${data.open_violation_count > 0 ? 'bg-red-50' : data.violation_count > 0 ? 'bg-yellow-50' : 'bg-green-50'}`}>
                {data.open_violation_count > 0 ? 
                  <AlertTriangle className="h-6 w-6 text-red-500 mt-1 flex-shrink-0" /> :
                  data.violation_count > 0 ?
                  <AlertTriangle className="h-6 w-6 text-yellow-500 mt-1 flex-shrink-0" /> :
                  <CheckCircle className="h-6 w-6 text-green-500 mt-1 flex-shrink-0" />
                }
                <div className="ml-3">
                  <h4 className={`text-md font-semibold ${data.open_violation_count > 0 ? 'text-red-800' : data.violation_count > 0 ? 'text-yellow-800' : 'text-green-800'}`}>
                    L&I Violations
                  </h4>
                  <p className="text-sm text-gray-600">
                    {data.open_violation_count > 0 && `${data.open_violation_count} OPEN violations | `}
                    {data.violation_count} total violations on record
                  </p>
                </div>
              </div>

              <div className="flex items-start p-3 rounded-lg bg-blue-50">
                <CheckCircle className="h-6 w-6 text-blue-500 mt-1 flex-shrink-0" />
                <div className="ml-3">
                  <h4 className="text-md font-semibold text-blue-800">Construction Permits</h4>
                  <p className="text-sm text-gray-600">{data.permit_count} permits issued</p>
                </div>
              </div>
            </div>
          </div>

          <div className="p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mr-2 text-blue-600">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                <polyline points="9 22 9 12 15 12 15 22"></polyline>
              </svg>
              Property Details
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Age:</span>
                  <span className="font-semibold">{data.property_age} years</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Bedrooms:</span>
                  <span className="font-semibold">{data.bedrooms || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Bathrooms:</span>
                  <span className="font-semibold">{data.bathrooms || 'N/A'}</span>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Living Area:</span>
                  <span className="font-semibold">{data.livable_area ? `${data.livable_area} sq ft` : 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Central Air:</span>
                  <span className="font-semibold">{data.has_central_air ? 'Yes ✓' : 'No'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Condition:</span>
                  <span className="font-semibold">{data.exterior_condition || 'N/A'}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white p-6">
          <h3 className="text-xl font-semibold text-gray-800 mb-4">Student Warnings</h3>
          
          {data.student_warnings && data.student_warnings.length > 0 ? (
            <div className="space-y-3">
              {data.student_warnings.map((warning, idx) => (
                <div key={idx} className="bg-yellow-50 border-l-4 border-yellow-400 p-3">
                  <div className="flex items-start">
                    <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5 flex-shrink-0" />
                    <p className="ml-2 text-sm text-yellow-800">{warning}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-green-50 border-l-4 border-green-400 p-4">
              <div className="flex items-center">
                <CheckCircle className="h-5 w-5 text-green-600" />
                <p className="ml-2 text-sm text-green-800">No major warnings found!</p>
              </div>
            </div>
          )}

          {data.risk_flags && data.risk_flags.length > 0 && (
            <div className="mt-6">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Risk Flags:</h4>
              <div className="space-y-1">
                {data.risk_flags.map((flag, idx) => (
                  <div key={idx} className="text-xs bg-gray-100 px-2 py-1 rounded">
                    {flag.replace(/_/g, ' ')}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="mt-8 p-4 bg-blue-50 rounded-lg">
            <h4 className="font-semibold text-blue-900 mb-2">What does this mean?</h4>
            <p className="text-sm text-blue-800">
              The trustability score combines safety, maintenance, and landlord quality to help students make informed housing decisions.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}