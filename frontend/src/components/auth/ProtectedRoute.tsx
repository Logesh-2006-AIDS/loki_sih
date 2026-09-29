import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { authService } from '../../services/authService';

interface ProtectedRouteProps {
  allowedRoles?: Array<'APPLICANT' | 'OFFICER' | 'COMMITTEE' | 'ADMIN'>;
  children: React.ReactNode;
}

export const getRoleDashboard = (role?: string): string => {
  switch (role) {
    case 'APPLICANT':
      return '/applicant/dashboard';
    case 'OFFICER':
      return '/officer/dashboard';
    case 'COMMITTEE':
      return '/committee';
    case 'ADMIN':
      return '/admin/schemes';
    default:
      return '/';
  }
};

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ allowedRoles, children }) => {
  const location = useLocation();
  const isAuthenticated = authService.isAuthenticated();
  const currentUser = authService.getCurrentUser();

  if (!isAuthenticated || !currentUser) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && allowedRoles.length > 0 && !allowedRoles.includes(currentUser.role as any)) {
    // Cross-role access attempt: redirect user to their own canonical dashboard
    const userDashboard = getRoleDashboard(currentUser.role);
    return <Navigate to={userDashboard} replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
