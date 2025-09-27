// App.js
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE_URL = 'http://localhost:8000/api';

function App() {
  const [currentView, setCurrentView] = useState('login');
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    if (token) {
      // Проверяем валидность токена
      verifyToken();
    }
  }, [token]);

  const verifyToken = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(response.data);
      setCurrentView('main');
    } catch (error) {
      localStorage.removeItem('token');
      setToken(null);
    }
  };

  const handleLogin = (userData, authToken) => {
    setUser(userData);
    setToken(authToken);
    localStorage.setItem('token', authToken);
    setCurrentView('main');
  };

  const handleLogout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    setCurrentView('login');
  };

  return (
    <div className="App">
      {currentView === 'login' && (
        <LoginView onLogin={handleLogin} />
      )}
      {currentView === 'main' && user && (
        <MainView user={user} onLogout={handleLogout} />
      )}
    </div>
  );
}

// Компонент авторизации
function LoginView({ onLogin }) {
  const [formData, setFormData] = useState({
    badge_id: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    if (e && e.preventDefault) {
      e.preventDefault();
    }
    
    setLoading(true);
    setError('');

    // Демо-режим - пропускаем реальный запрос к API
    if (formData.badge_id === 'demo' || formData.badge_id === 'admin') {
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const demoUser = {
        id: 1,
        badge_id: formData.badge_id,
        full_name: formData.badge_id === 'admin' ? 'Администратор Системы' : 'Иванов Иван Иванович',
        is_active: true,
        is_superuser: formData.badge_id === 'admin'
      };
      
      onLogin(demoUser, 'demo-jwt-token');
      setLoading(false);
      return;
    }

    try {
      const response = await axios.post(`${API_BASE_URL}/auth/login`, formData);
      onLogin(response.data.user, response.data.access_token);
    } catch (error) {
      setError('Ошибка авторизации. Проверьте badge_id и пароль.');
      
      await new Promise(resolve => setTimeout(resolve, 1000));
      const demoUser = {
        id: 1,
        badge_id: 'demo',
        full_name: 'Демо Пользователь',
        is_active: true,
        is_superuser: false
      };
      onLogin(demoUser, 'demo-jwt-token');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleQuickLogin = async (badgeId) => {
    setLoading(true);
    
    setFormData({ 
      badge_id: badgeId, 
      password: 'password' 
    });

    await new Promise(resolve => setTimeout(resolve, 100));
    
    const demoUser = {
      id: 1,
      badge_id: badgeId,
      full_name: badgeId === 'admin' ? 'Администратор Системы' : 'Иванов Иван Иванович',
      is_active: true,
      is_superuser: badgeId === 'admin'
    };
    
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    onLogin(demoUser, 'demo-jwt-token');
    setLoading(false);
  };

  return (
    <div className="login-container">
      <div className="login-form">
        <h2>Авторизация оператора</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Badge ID:</label>
            <input
              type="text"
              name="badge_id"
              value={formData.badge_id}
              onChange={handleChange}
              required
              disabled={loading}
            />
          </div>
          <div className="form-group">
            <label>Пароль:</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
              disabled={loading}
            />
          </div>
          {error && <div className="error-message">{error}</div>}
          <button type="submit" disabled={loading}>
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>

        <div className="quick-login-buttons">
          <p style={{textAlign: 'center', margin: '1rem 0', color: '#666'}}>Или войдите быстро:</p>
          <button 
            onClick={() => handleQuickLogin('demo')}
            disabled={loading}
            className="quick-login-btn demo-btn"
          >
            {loading ? 'Вход...' : 'Быстрый вход (Demo пользователь)'}
          </button>

          <button 
            onClick={() => handleQuickLogin('admin')}
            disabled={loading}
            className="quick-login-btn admin-btn"
          >
            {loading ? 'Вход...' : 'Вход как Администратор'}
          </button>
        </div>

        <div className="demo-info">
          <p>
            <strong>Демо-режим:</strong> Используйте кнопки быстрого входа или введите любые данные в форму
          </p>
        </div>
      </div>
    </div>
  );
}

// Главный компонент работы с инструментами
function MainView({ user, onLogout }) {
  const [engineer, setEngineer] = useState('');
  const [operationType, setOperationType] = useState('checkout');
  const [operationDate, setOperationDate] = useState('');
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [sessionId, setSessionId] = useState(null);

  // Устанавливаем текущую дату по умолчанию при загрузке
  useEffect(() => {
    const now = new Date();
    const localDateTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 16);
    setOperationDate(localDateTime);
  }, []);

  const handleImageUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const base64 = e.target.result;
            // Сохраняем base64 для отправки на сервер
            setUploadedImage(base64);
        };
        reader.readAsDataURL(file);
    }
};

  const startScanning = async () => {
    if (!engineer.trim()) {
      alert('Введите ФИО инженера');
      return;
    }

    if (!operationDate) {
      alert('Выберите дату и время операции');
      return;
    }

    setScanning(true);
    setLoading(true);

    try {
      // Начинаем новую операцию
      const operationData = {
        engineer_name: engineer,
        operation_type: operationType,
        operation_date: operationDate,
        user_id: user.id
      };

      const response = await axios.post(`${API_BASE_URL}/operations/start`, operationData, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });

      setSessionId(response.data.session_id);
      
      // Имитация сканирования
      simulateScanning(response.data.session_id);
      
    } catch (error) {
      console.error('Ошибка начала операции:', error);
      setScanning(false);
      setLoading(false);
    }
  };

  const simulateScanning = async (sessionId) => {
    try {
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      // Демо-данные инструментов
      const demoTools = [
        { id: 1, class_name: "Молоток", confidence: 95.5, detected_quantity: 1 },
        { id: 2, class_name: "Отвертка крестовая", confidence: 87.3, detected_quantity: 2 },
        { id: 3, class_name: "Гаечный ключ", confidence: 92.1, detected_quantity: 3 },
        { id: 4, class_name: "Плоскогубцы", confidence: 78.9, detected_quantity: 1 }
      ];
      
      setTools(demoTools.map(tool => ({
        ...tool,
        manual_quantity: tool.detected_quantity || 0,
        is_manual_edit: false
      })));

    } catch (error) {
      console.error('Ошибка сканирования:', error);
    } finally {
      setScanning(false);
      setLoading(false);
    }
  };

  const updateToolQuantity = (index, newQuantity) => {
    const updatedTools = [...tools];
    updatedTools[index] = {
      ...updatedTools[index],
      manual_quantity: Math.max(0, newQuantity),
      is_manual_edit: true
    };
    setTools(updatedTools);
  };

  const confirmOperation = async () => {
      if (!sessionId) return;

      setLoading(true);
      try {
          const operationData = {
              session_id: sessionId,
              operation_date: operationDate,
              tools: tools.map(tool => ({
                  tool_id: tool.id,
                  final_quantity: tool.manual_quantity,
                  was_manually_adjusted: tool.is_manual_edit
              })),
              image_base64: uploadedImage // Добавляем изображение если есть
          };

          const response = await axios.post(`${API_BASE_URL}/operations/confirm`, operationData);
          
          // Показываем результаты ML если использовались
          if (response.data.ml_used) {
              alert(`ML обнаружено ${response.data.total_tools} инструментов!`);
          }
          
          alert(`Операция успешно завершена!`);
          resetOperation();
          
      } catch (error) {
          console.error('Ошибка подтверждения операции:', error);
          alert('Ошибка при завершении операции');
      } finally {
          setLoading(false);
      }
  };

  const resetOperation = () => {
    setEngineer('');
    setTools([]);
    setSessionId(null);
    setScanning(false);
    // Сбрасываем дату на текущую
    const now = new Date();
    const localDateTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 16);
    setOperationDate(localDateTime);
  };

  const formatDateTime = (dateTimeString) => {
    const date = new Date(dateTimeString);
    return date.toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="main-container">
      <header className="header">
        <h1>Учет инструментов</h1>
        <div className="user-info">
          <span>Оператор: {user.full_name}</span>
          {user.is_superuser && <span className="admin-badge">ADMIN</span>}
          <button onClick={onLogout}>Выйти</button>
        </div>
      </header>

      <div className="operation-panel">
        <div className="input-section">
          <div className="form-group">
            <label>ФИО инженера:</label>
            <input
              type="text"
              value={engineer}
              onChange={(e) => setEngineer(e.target.value)}
              placeholder="Введите фамилию, имя, отчество"
              disabled={scanning || loading}
            />
          </div>

          <div className="form-group">
            <label>Тип операции:</label>
            <select
              value={operationType}
              onChange={(e) => setOperationType(e.target.value)}
              disabled={scanning || loading}
            >
              <option value="checkout">Выдал инструменты</option>
              <option value="checkin">Принял инструменты</option>
            </select>
          </div>

          <div className="form-group">
            <label>Дата и время операции:</label>
            <input
              type="datetime-local"
              value={operationDate}
              onChange={(e) => setOperationDate(e.target.value)}
              disabled={scanning || loading}
            />
            <small className="date-hint">
              Текущее время: {formatDateTime(new Date())}
            </small>
          </div>

          <div className="action-buttons">
            <button 
              onClick={startScanning}
              disabled={!engineer.trim() || !operationDate || scanning || loading}
              className="scan-button"
            >
              {scanning ? 'Сканирование...' : 'Начать сканирование'}
            </button>
            
            {tools.length > 0 && (
              <button 
                onClick={confirmOperation}
                disabled={loading}
                className="confirm-button"
              >
                {loading ? 'Сохранение...' : 'Подтвердить операцию'}
              </button>
            )}
          </div>
        </div>

        {scanning && (
          <div className="scanning-overlay">
            <div className="scanning-animation">
              <div className="scanner"></div>
              <p>Идет сканирование инструментов...</p>
              <p>Дата операции: {formatDateTime(operationDate)}</p>
            </div>
          </div>
        )}

        {tools.length > 0 && (
          <div className="tools-section">
            <div className="operation-info">
              <h3>Детали операции:</h3>
              <p><strong>Инженер:</strong> {engineer}</p>
              <p><strong>Тип операции:</strong> {operationType === 'checkout' ? 'Выдача' : 'Прием'}</p>
              <p><strong>Дата и время:</strong> {formatDateTime(operationDate)}</p>
            </div>
            
            <h3>Распознанные инструменты:</h3>
            <div className="tools-list">
              {tools.map((tool, index) => (
                <ToolItem
                  key={index}
                  tool={tool}
                  index={index}
                  onQuantityChange={updateToolQuantity}
                  operationType={operationType}
                />
              ))}
            </div>
            
            <div className="operation-summary">
              <p><strong>Итого инструментов:</strong> {tools.reduce((sum, tool) => sum + tool.manual_quantity, 0)}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Компонент отдельного инструмента
function ToolItem({ tool, index, onQuantityChange, operationType }) {
  const [localQuantity, setLocalQuantity] = useState(tool.manual_quantity);

  const handleQuantityChange = (newQuantity) => {
    setLocalQuantity(newQuantity);
    onQuantityChange(index, newQuantity);
  };

  return (
    <div className={`tool-item ${tool.is_manual_edit ? 'manual-edit' : ''}`}>
      <div className="tool-info">
        <span className="tool-name">{tool.class_name || tool.name}</span>
        {tool.confidence && (
          <span className="confidence">Точность: {tool.confidence.toFixed(1)}%</span>
        )}
      </div>
      
      <div className="quantity-controls">
        <button 
          onClick={() => handleQuantityChange(localQuantity - 1)}
          disabled={localQuantity <= 0}
        >
          -
        </button>
        
        <input
          type="number"
          value={localQuantity}
          onChange={(e) => handleQuantityChange(parseInt(e.target.value) || 0)}
          min="0"
        />
        
        <button onClick={() => handleQuantityChange(localQuantity + 1)}>
          +
        </button>
      </div>
      
      <div className="operation-indicator">
        {operationType === 'checkout' ? '📤 Выдача' : '📥 Прием'}
      </div>
    </div>
  );
}

export default App;