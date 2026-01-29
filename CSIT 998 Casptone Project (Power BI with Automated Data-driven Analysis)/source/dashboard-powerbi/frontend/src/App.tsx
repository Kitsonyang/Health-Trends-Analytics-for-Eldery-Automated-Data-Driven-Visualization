import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './routes/ProtectedRoute'
import SidebarLayout from './layout/SidebarLayout'
import { lazy, Suspense } from 'react'
import { App as AntdApp, ConfigProvider } from 'antd'
import { PBIRefreshProvider } from './context/PBIRefreshContext'

const Login = lazy(() => import('./pages/Login'))
const Register = lazy(() => import('./pages/Register'))
const PowerBIEmbed = lazy(() => import('./pages/PowerBIEmbed'))
const PowerBIDebug = lazy(() => import('./pages/PowerBIDebug'))
const ImportFiles = lazy(() => import('./pages/ImportFiles'))
const MachineLearning = lazy(() => import('./pages/MachineLearning'))
const SymptomsVsCategories = lazy(() => import('./pages/SymptomsVsCategories'))

function App() {
  return (
    <ConfigProvider
      theme={{
        token: {
          // You can customize theme tokens here if needed
        },
      }}
    >
      <AntdApp notification={{ top: 70 }}>
        <BrowserRouter>
          <AuthProvider>
            <PBIRefreshProvider>
            <Routes>
            <Route path="/login" element={<Suspense fallback={null}><Login /></Suspense>} />
            <Route path="/register" element={<Suspense fallback={null}><Register /></Suspense>} />

            <Route element={<ProtectedRoute />}>
            <Route
              path="/"
              element={
                <SidebarLayout>
                  <Navigate to="/dashboard" replace />
                </SidebarLayout>
              }
            />
            <Route
              path="/dashboard"
              element={
                <SidebarLayout>
                  <Suspense fallback={null}><PowerBIEmbed /></Suspense>
                </SidebarLayout>
              }
            />
            <Route
              path="/refresh-history"
              element={
                <SidebarLayout>
                  <Suspense fallback={null}><PowerBIDebug /></Suspense>
                </SidebarLayout>
              }
            />
            <Route element={<ProtectedRoute roles={["admin"]} />}>
              <Route
                path="/import"
                element={
                <SidebarLayout>
                  <Suspense fallback={null}><ImportFiles /></Suspense>
                </SidebarLayout>
                }
              />
            </Route>
            <Route
              path="/ml"
              element={
                <SidebarLayout>
                  <Suspense fallback={null}><MachineLearning /></Suspense>
                </SidebarLayout>
              }
            />
            {/* PowerBIApi page hidden */}
            {/* cluster-visuals route removed from navigation; keeping route removed */}
            <Route element={<ProtectedRoute roles={["admin"]} />}>
              <Route
                path="/symptoms"
                element={
                <SidebarLayout>
                  <Suspense fallback={null}><SymptomsVsCategories /></Suspense>
                </SidebarLayout>
                }
              />
            </Route>
            {/* settings/help routes removed */}
          </Route>
        </Routes>
            </PBIRefreshProvider>
          </AuthProvider>
      </BrowserRouter>
      </AntdApp>
    </ConfigProvider>
  )
}

export default App
