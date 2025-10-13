import React from 'react';

import Image01 from '../../images/user-36-05.jpg';
import Image02 from '../../images/user-36-06.jpg';
import Image03 from '../../images/user-36-07.jpg';
import Image04 from '../../images/user-36-08.jpg';
import Image05 from '../../images/user-36-09.jpg';

function ProvidersCard() {

  const providers = [
    {
      id: '0',
      image: Image01,
      name: 'Riley Nelson',
      contract_type: 'IC',
      shift_preference: 'MD1, MD2, PM',
      total_shifts: '5',
      weekend_shifts: '4',
      night_shifts: '1',
      next_shift: 'Jan 22',
    },
    {
      id: '1',
      image: Image02,
      name: 'Miles Walker',
      contract_type: 'FT',
      shift_preference: 'MD1, PM',
      total_shifts: '6',
      weekend_shifts: '1',
      night_shifts: '1',
      next_shift: 'Jan 21',
    },
    {
      id: '2',
      image: Image03,
      name: 'Spencer Stevens',
      contract_type: 'FT',
      shift_preference: 'MD1, PM',
      total_shifts: '8',
      weekend_shifts: '0',
      night_shifts: '1',
      next_shift: 'Jan 28',
    },
    {
      id: '3',
      image: Image04,
      name: 'Jordan Brooks',
      contract_type: 'IC',
      shift_preference: 'PM',
      total_shifts: '1',
      weekend_shifts: '0',
      night_shifts: '1',
      next_shift: 'Jan 17',
    },
    {
      id: '4',
      image: Image05,
      name: 'Cameron Walker',
      contract_type: 'IC',
      shift_preference: 'MD1, PM',
      total_shifts: '4',
      weekend_shifts: '1',
      night_shifts: '2',
      next_shift: 'Jan 19',
    },
  ];

  return (
    <div className="col-span-full xl:col-span-6 bg-white dark:bg-gray-800 shadow-xs rounded-xl">
      <header className="px-5 py-4 border-b border-gray-100 dark:border-gray-700/60">
        <h2 className="font-semibold text-gray-800 dark:text-gray-100">Providers</h2>
      </header>      
      <div className="p-3">

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="table-auto w-full">
            {/* Table header */}
            <thead className="text-xs font-semibold uppercase text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-700/50">
              <tr>
                <th className="p-2 whitespace-nowrap">
                  <div className="font-semibold text-left">Name</div>
                </th>
                <th className="p-2 whitespace-nowrap">
                  <div className="font-semibold text-left">Contract Type</div>
                </th>
                <th className="p-2 whitespace-nowrap">
                  <div className="font-semibold text-left">Shift Preference</div>
                </th>
                <th className="p-2 whitespace-nowrap">
                  <div className="font-semibold text-center">Total Shifts</div>
                </th>
                <th className="p-2 whitespace-nowrap">
                  <div className="font-semibold text-center">Weekend Shifts</div>
                </th>
                <th className="p-2 whitespace-nowrap">
                  <div className="font-semibold text-center">Night Shifts</div>
                </th>
                <th className="p-2 whitespace-nowrap">
                  <div className="font-semibold text-center">Next Shift</div>
                </th>
              </tr>
            </thead>
            {/* Table body */}
            <tbody className="text-sm divide-y divide-gray-100 dark:divide-gray-700/60">
              {
                providers.map(provider => {
                  return (
                    <tr key={provider.id}>
                      <td className="p-2 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="w-10 h-10 shrink-0 mr-2 sm:mr-3">
                            <img className="rounded-full" src={provider.image} width="40" height="40" alt={provider.name} />
                          </div>
                          <div className="font-medium text-gray-800 dark:text-gray-100">{provider.name}</div>
                        </div>
                      </td>
                      <td className="p-2 whitespace-nowrap">
                        <div className="text-left">{provider.contract_type}</div>
                      </td>
                      <td className="p-2 whitespace-nowrap">
                        <div className="text-left font-medium text-green-500">{provider.shift_preference}</div>
                      </td>
                      <td className="p-2 whitespace-nowrap">
                        <div className="text-lg text-center">{provider.total_shifts}</div>
                      </td>
                      <td className="p-2 whitespace-nowrap">
                        <div className="text-lg text-center">{provider.weekend_shifts}</div>
                      </td>
                      <td className="p-2 whitespace-nowrap">
                        <div className="text-lg text-center">{provider.night_shifts}</div>
                      </td>
                      <td className="p-2 whitespace-nowrap">
                        <div className="text-lg text-center">{provider.next_shift}</div>
                      </td>
                    </tr>
                  )
                })
              }
            </tbody>
          </table>

        </div>

      </div>
    </div>
  );
}

export default ProvidersCard;
