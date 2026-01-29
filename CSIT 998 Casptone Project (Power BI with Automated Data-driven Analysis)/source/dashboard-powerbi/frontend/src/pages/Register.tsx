/**
 * User Registration Page Component
 * 
 * New user registration interface with role selection (user/admin)
 * and client-side validation.
 * 
 * @component
 */

import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, Typography, App, Card, Radio } from 'antd';
import { useState } from 'react';
import { authRegister } from '../api/client';
import { UserOutlined, LockOutlined } from '@ant-design/icons';

export default function Register() {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);

  async function onFinish(values: { username: string; password: string; confirmPassword: string; role: string }) {
    const { username, password, confirmPassword, role } = values;
    
    if (!username?.trim()) {
      message.error('Please enter username');
      return;
    }

    if (username.trim().length < 3) {
      message.error('Username must be at least 3 characters');
      return;
    }

    if (!password || password.length < 6) {
      message.error('Password must be at least 6 characters');
      return;
    }

    if (password !== confirmPassword) {
      message.error('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      const result = await authRegister({
        username: username.trim(),
        password: password,
        role: role || 'user',
      });

      if (result.ok) {
        message.success('Registration successful! Please login.', 2);
        // Navigate after delay to let user see success message
        setTimeout(() => navigate('/login'), 2000);
      } else {
        message.error('Registration failed');
      }
    } catch (error: any) {
      console.error('Registration error:', error);
      message.error(error.message || 'Registration failed, username may already exist');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f6fa', padding: 16 }}>
      <Card style={{ width: 420 }}>
        <Typography.Title level={3} style={{ textAlign: 'center', marginBottom: 8 }}>Sign Up</Typography.Title>
        <Typography.Paragraph style={{ textAlign: 'center', color: '#636e72', marginBottom: 24 }}>
          Create a new account
        </Typography.Paragraph>

        <Form layout="vertical" onFinish={onFinish} initialValues={{ role: 'user' }}>
          <Form.Item 
            label="Username" 
            name="username" 
            rules={[
              { required: true, message: 'Please enter username' },
              { min: 3, message: 'Username must be at least 3 characters' }
            ]}
          >
            <Input 
              prefix={<UserOutlined style={{ color: '#1677ff' }} />}
              placeholder="Enter username (at least 3 characters)" 
              autoComplete="username" 
            />
          </Form.Item>

          <Form.Item 
            label="Password" 
            name="password" 
            rules={[
              { required: true, message: 'Please enter password' },
              { min: 6, message: 'Password must be at least 6 characters' }
            ]}
          >
            <Input.Password 
              prefix={<LockOutlined style={{ color: '#1677ff' }} />}
              placeholder="Enter password (at least 6 characters)" 
              autoComplete="new-password" 
            />
          </Form.Item>

          <Form.Item 
            label="Confirm Password" 
            name="confirmPassword" 
            dependencies={['password']}
            rules={[
              { required: true, message: 'Please confirm your password' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('Passwords do not match'));
                },
              }),
            ]}
          >
            <Input.Password 
              prefix={<LockOutlined style={{ color: '#1677ff' }} />}
              placeholder="Confirm your password" 
              autoComplete="new-password" 
            />
          </Form.Item>

          <Form.Item label="Role" name="role">
            <Radio.Group>
              <Radio value="user">User</Radio>
              <Radio value="admin">Admin</Radio>
            </Radio.Group>
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>
              Sign Up
            </Button>
          </Form.Item>
        </Form>

        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Typography.Text type="secondary">
            Already have an account?{' '}
            <Button type="link" onClick={() => navigate('/login')} style={{ padding: 0 }}>
              Sign In
            </Button>
          </Typography.Text>
        </div>
      </Card>
    </div>
  );
}

