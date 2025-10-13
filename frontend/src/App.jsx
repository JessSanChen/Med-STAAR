import React, { useEffect } from 'react';
import {
  Routes,
  Route,
  useLocation
} from 'react-router-dom';

import './css/style.css';

import './charts/ChartjsConfig';

// Import pages
import Dashboard from './pages/Dashboard';
import ProviderContracts from './pages/ProviderContracts';
import FacilityCoverage from './pages/FacilityCoverage';
import FacilityVolume from './pages/FacilityVolume';
import ProviderAvailability from './pages/ProviderAvailability';
import ProviderCredentialing from './pages/ProviderCredentialing';
import Scheduler from './pages/Scheduler';
import PredictedVolume from './pages/PredictedVolume';
import AddProvider from './pages/AddProvider';
import FairnessReport from './pages/FairnessReport';
import Rescheduler from './pages/Rescheduler';

function App() {

  const location = useLocation();

  useEffect(() => {
    document.querySelector('html').style.scrollBehavior = 'auto'
    window.scroll({ top: 0 })
    document.querySelector('html').style.scrollBehavior = ''
  }, [location.pathname]); // triggered on route change

  return (
    <>
      <Routes>
        <Route exact path="/" element={<Dashboard />} />
        <Route exact path="/provider-contracts" element={<ProviderContracts />} />
        <Route path="/facility-coverage" element={<FacilityCoverage />} />
        <Route path="/facility-volume" element={<FacilityVolume />} />
        <Route path="/provider-availabilities" element={<ProviderAvailability />} />
        <Route path="/provider-credentialing" element={<ProviderCredentialing />} />
        <Route path="/scheduler" element={<Scheduler />} />
        <Route path="/predicted-volume" element={<PredictedVolume />} />
        <Route path="/add-providers" element={<AddProvider />} />
        <Route path="/fairness-report" element={<FairnessReport />} />
        <Route path="/rescheduler" element={<Rescheduler />} />



      </Routes>
    </>
  );
}

export default App;
