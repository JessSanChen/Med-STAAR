import React, { useState } from 'react';

const SHIFT_OPTIONS = ['MD1', 'MD2', 'PM'];
const CONTRACT_TYPES = ['FT', 'PT', 'IC', 'PRN'];

function AddProviderForm() {
  const [submitted, setSubmitted] = useState(false);
  const [values, setValues] = useState({
    name: '',
    email: '',
    phone: '',
    contractType: '',
    shiftPrefs: [],
    maxShifts: '',
    maxWeekendShifts: '',
    maxNightShifts: '',
    credentials: '',
    education: '',
    licenses: '',
    certifications: '',
    affiliations: '',
    notes: '',
  });

  const onChange = (e) => {
    const { name, value } = e.target;
    setValues((v) => ({ ...v, [name]: value }));
  };

  const onToggleShift = (shift) => {
    setValues((v) => {
      const has = v.shiftPrefs.includes(shift);
      return { ...v, shiftPrefs: has ? v.shiftPrefs.filter(s => s !== shift) : [...v.shiftPrefs, shift] };
    });
  };

  const onSubmit = (e) => {
    e.preventDefault();
    // no backend: simply acknowledge
    setSubmitted(true);
    // (optional) reset after submit:
    // setValues({ ...initial });
  };

  if (submitted) {
    return (
      <div className="p-4 border border-green-200 dark:border-green-900 rounded-lg bg-green-50 dark:bg-green-900/20">
        <div className="text-green-700 dark:text-green-300 font-medium">Provider added!</div>
        <div className="text-sm text-gray-600 dark:text-gray-300 mt-1">
          <span className="font-medium">Name:</span> {values.name || '—'} · <span className="font-medium">Contract:</span> {values.contractType || '—'} · <span className="font-medium">Shifts:</span> {values.shiftPrefs.join(', ') || '—'}
        </div>
        <button
          onClick={() => setSubmitted(false)}
          className="mt-3 text-sm px-3 py-1.5 rounded-md border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700"
        >
          Add another
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      {/* Basic Info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">Full Name *</label>
          <input
            name="name"
            value={values.name}
            onChange={onChange}
            required
            className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
            placeholder="e.g., Riley Nelson"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">Contract Type *</label>
          <select
            name="contractType"
            value={values.contractType}
            onChange={onChange}
            required
            className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
          >
            <option value="">Select</option>
            {CONTRACT_TYPES.map((ct) => <option key={ct} value={ct}>{ct}</option>)}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">Email</label>
          <input
            type="email"
            name="email"
            value={values.email}
            onChange={onChange}
            className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
            placeholder="name@example.com"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">Phone</label>
          <input
            name="phone"
            value={values.phone}
            onChange={onChange}
            className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
            placeholder="(555) 555-5555"
          />
        </div>
      </div>

      {/* Shift Preferences */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">Shift Preference</label>
        <div className="flex gap-4">
          {SHIFT_OPTIONS.map((opt) => (
            <label key={opt} className="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
              <input
                type="checkbox"
                checked={values.shiftPrefs.includes(opt)}
                onChange={() => onToggleShift(opt)}
                className="rounded border-gray-300 dark:border-gray-600"
              />
              {opt}
            </label>
          ))}
        </div>
      </div>

      {/* Limits */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">Max Shifts / Month</label>
          <input
            type="number"
            name="maxShifts"
            value={values.maxShifts}
            onChange={onChange}
            min="0"
            className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
            placeholder="e.g., 15"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">Max Weekend Shifts / Month</label>
          <input
            type="number"
            name="maxWeekendShifts"
            value={values.maxWeekendShifts}
            onChange={onChange}
            min="0"
            className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
            placeholder="e.g., 4"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-2 00">Max Night Shifts / Month</label>
          <input
            type="number"
            name="maxNightShifts"
            value={values.maxNightShifts}
            onChange={onChange}
            min="0"
            className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
            placeholder="e.g., 2"
          />
        </div>
      </div>

      {/* Text areas */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">Credentials</label>
          <textarea
            name="credentials"
            value={values.credentials}
            onChange={onChange}
            rows="3"
            className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
            placeholder="e.g., MD, DO"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">Education</label>
          <textarea
            name="education"
            value={values.education}
            onChange={onChange}
            rows="3"
            className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
            placeholder="Medical school, residency, fellowship"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">Licenses</label>
          <textarea
            name="licenses"
            value={values.licenses}
            onChange={onChange}
            rows="3"
            className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
            placeholder="State licenses"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">Certifications</label>
          <textarea
            name="certifications"
            value={values.certifications}
            onChange={onChange}
            rows="3"
            className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
            placeholder="Board certifications, ACLS/BLS, etc."
          />
        </div>
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">Affiliations</label>
          <textarea
            name="affiliations"
            value={values.affiliations}
            onChange={onChange}
            rows="3"
            className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
            placeholder="Hospitals, groups, associations"
          />
        </div>
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">Notes (optional)</label>
          <textarea
            name="notes"
            value={values.notes}
            onChange={onChange}
            rows="3"
            className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
            placeholder="Anything else important"
          />
        </div>
      </div>

      {/* Submit */}
      <div className="pt-2">
        <button
          type="submit"
          className="inline-flex items-center gap-2 rounded-md bg-violet-600 hover:bg-violet-700 text-white text-sm font-medium px-4 py-2"
        >
          Add Provider
        </button>
      </div>
    </form>
  );
}

export default AddProviderForm;
