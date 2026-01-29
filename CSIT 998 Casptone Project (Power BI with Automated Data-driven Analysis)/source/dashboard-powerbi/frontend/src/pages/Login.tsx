/**
 * Login Page Component
 * 
 * User authentication interface with username/password form and
 * optional "Remember Me" functionality.
 * 
 * @component
 */

import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Form, Input, Button, Typography, App, Card, Checkbox } from 'antd';
import { useState } from 'react';
import { authLogin } from '../api/client';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  async function onFinish(values: { username: string; password: string; remember?: boolean }) {
    const { username, password, remember } = values;
    
    if (!username?.trim() || !password?.trim()) {
      message.error('Please enter username and password');
      return;
    }

    setLoading(true);
    try {
      const result = await authLogin({
        username: username.trim(),
        password: password,
      });

      if (result.ok) {
        message.success('Login successful!');
        login(result.user.username, result.user.role as any, result.token, remember);
        // Navigate after brief delay to allow success message to display
        setTimeout(() => navigate('/'), 500);
      } else {
        message.error('Login failed');
      }
    } catch (error: any) {
      console.error('Login error:', error);
      message.error(error.message || 'Login failed, please check your credentials');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f6fa', padding: 16 }}>
      <Card style={{ width: 420 }}>
        <Typography.Title level={3} style={{ textAlign: 'center', marginBottom: 8 }}>Sign In</Typography.Title>
        <Typography.Paragraph style={{ textAlign: 'center', color: '#636e72', marginBottom: 16 }}>
          Enter your account and password
        </Typography.Paragraph>
        <Form layout="vertical" onFinish={onFinish} form={form}>
          <Form.Item label="Username" name="username" rules={[{ required: true, message: 'Please enter username' }]}>
            <Input placeholder="Enter username" autoComplete="username" />
          </Form.Item>
          <Form.Item label="Password" name="password" rules={[{ required: true, message: 'Please enter password' }]}>
            <Input.Password placeholder="Enter password" autoComplete="current-password" />
          </Form.Item>
          <Form.Item>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Form.Item name="remember" valuePropName="checked" noStyle>
                <Checkbox>Remember me</Checkbox>
              </Form.Item>
            </div>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>Sign In</Button>
          </Form.Item>
        </Form>

        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Typography.Text type="secondary">
            Don't have an account?{' '}
            <Button type="link" onClick={() => navigate('/register')} style={{ padding: 0 }}>
              Sign Up
            </Button>
          </Typography.Text>
        </div>
      </Card>
    </div>
  );
}


