import { useEffect } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from '../features/auth/AuthContext';
import { AccountProvider } from '../features/account/AccountContext';
import { initTheme, watchSystemTheme } from '../utils/theme';
import { ProtectedLayout } from './ProtectedLayout';
import { Toaster } from '../components/ui';
import { SignInPage } from '../features/auth/SignInPage';
import { SignUpPage } from '../features/auth/SignUpPage';
import { DashboardPage } from '../features/dashboard/DashboardPage';
import { ProfilePage } from '../features/financial-profile/ProfilePage';
import { AccountProfilePage } from '../features/account/AccountProfilePage';
import { SettingsPage } from '../features/account/SettingsPage';
import { AffordabilityPage } from '../features/affordability/AffordabilityPage';
import { DecisionDetailPage } from '../features/history/DecisionDetailPage';
import { HistoryPage } from '../features/history/HistoryPage';

export default function App() {
  useEffect(() => {
    initTheme();
    return watchSystemTheme();
  }, []);

  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/signin" element={<SignInPage />} />
          <Route path="/signup" element={<SignUpPage />} />
          <Route element={
            <AuthProvider>
              <AccountProvider>
                <ProtectedLayout />
              </AccountProvider>
            </AuthProvider>
          }>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/profile" element={<AccountProfilePage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/financial-profile" element={<ProfilePage />} />
            <Route path="/affordability" element={<AffordabilityPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/history/:id" element={<DecisionDetailPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Toaster />
      </BrowserRouter>
    </AuthProvider>
  );
}
