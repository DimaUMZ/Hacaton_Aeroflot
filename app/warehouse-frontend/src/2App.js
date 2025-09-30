import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE_URL = 'http://localhost:8001/api';

// Объект с описаниями ошибок
const ERROR_CODES = {
  NETWORK_ERROR: {
    code: 'ERR_001',
    message: 'Сервер недоступен. Проверьте подключение к сети и запущен ли бэкенд-сервер.'
  },
  AUTH_ERROR: {
    code: 'ERR_002', 
    message: 'Ошибка авторизации. Проверьте правильность badge_id и пароля.'
  },
  DETECTION_ERROR: {
    code: 'ERR_003',
    message: 'Ошибка распознавания инструментов. Сервис компьютерного зрения недоступен.'
  },
  OPERATION_START_ERROR: {
    code: 'ERR_004',
    message: 'Ошибка начала операции. Не удалось создать сессию для работы с инструментами.'
  },
  OPERATION_CONFIRM_ERROR: {
    code: 'ERR_005',
    message: 'Ошибка подтверждения операции. Не удалось сохранить данные операции.'
  },
  CAMERA_ERROR: {
    code: 'ERR_006',
    message: 'Ошибка доступа к камере. Разрешите доступ к камере в настройках браузера.'
  }
};

function App() {
  const [currentView, setCurrentView] = useState('login');
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    if (token) {
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
      if (error.code === 'NETWORK_ERROR' || !error.response) {
        showError(ERROR_CODES.NETWORK_ERROR);
      } else {
        localStorage.removeItem('token');
        setToken(null);
      }
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

  // Функция для показа ошибок
  const showError = (errorInfo) => {
    alert(`Ошибка ${errorInfo.code}: ${errorInfo.message}`);
  };

  return (
    <div className="App">
      {currentView === 'login' && (
        <LoginView onLogin={handleLogin} showError={showError} />
      )}
      {currentView === 'main' && user && (
        <MainView user={user} onLogout={handleLogout} showError={showError} />
      )}
    </div>
  );
}

// Компонент авторизации
function LoginView({ onLogin, showError }) {
  const [formData, setFormData] = useState({
    badge_id: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API_BASE_URL}/auth/login`, formData);
      onLogin(response.data.user, response.data.access_token);
    } catch (error) {
      console.error('Login error:', error);
      
      if (error.code === 'NETWORK_ERROR' || error.response?.status >= 500) {
        showError(ERROR_CODES.NETWORK_ERROR);
        setError('Бэкенд недоступен. Проверьте подключение к серверу.');
      } else {
        showError(ERROR_CODES.AUTH_ERROR);
        setError('Ошибка авторизации. Проверьте badge_id и пароль.');
      }
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
    
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/login`, {
        badge_id: badgeId,
        password: badgeId === 'admin' ? 'admin' : 'password'
      });
      onLogin(response.data.user, response.data.access_token);
    } catch (error) {
      if (error.code === 'NETWORK_ERROR' || error.response?.status >= 500) {
        showError(ERROR_CODES.NETWORK_ERROR);
      } else {
        showError(ERROR_CODES.AUTH_ERROR);
      }
    } finally {
      setLoading(false);
    }
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
              placeholder="demo или admin"
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
              placeholder="password"
            />
          </div>
          {error && <div className="error-message">{error}</div>}
          <button type="submit" disabled={loading}>
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>

        <div className="quick-login-buttons">
          <p style={{textAlign: 'center', margin: '1rem 0', color: '#666'}}>Быстрый вход:</p>
          <button 
            onClick={() => handleQuickLogin('demo')}
            disabled={loading}
            className="quick-login-btn demo-btn"
          >
            Демо пользователь
          </button>

          <button 
            onClick={() => handleQuickLogin('admin')}
            disabled={loading}
            className="quick-login-btn admin-btn"
          >
            Администратор
          </button>
        </div>

        <div className="demo-info">
          <p><strong>Данные для входа:</strong></p>
          <p>• Демо: badge_id = demo, пароль = password</p>
          <p>• Админ: badge_id = admin, пароль = admin</p>
        </div>
      </div>
    </div>
  );
}

// Главный компонент работы с инструментами
function MainView({ user, onLogout, showError }) {
  const [engineer, setEngineer] = useState('');
  const [operationType, setOperationType] = useState('checkout');
  const [operationDate, setOperationDate] = useState('');
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [uploadedImage, setUploadedImage] = useState(null);
  
  // Состояния для камеры
  const [cameraActive, setCameraActive] = useState(false);
  const videoRef = useRef(null);
  const [stream, setStream] = useState(null);

  // Устанавливаем текущую дату по умолчанию
  useEffect(() => {
    const now = new Date();
    const localDateTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 16);
    setOperationDate(localDateTime);
  }, []);


  
  // Активация камеры
  const startCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 1280, height: 720 } 
      });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
      setCameraActive(true);
    } catch (error) {
      console.error('Ошибка доступа к камере:', error);
      showError(ERROR_CODES.CAMERA_ERROR);
    }
  };

  // Остановка камеры
  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
    setCameraActive(false);
  };

  

  // Захват кадра и отправка на бэкенд
  const captureAndDetect = async () => {
    if (!videoRef.current || !cameraActive) {
      alert('Камера не активирована');
      return;
    }

    const canvas = document.createElement('canvas');
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(videoRef.current, 0, 0);
    
    const imageBase64 = canvas.toDataURL('image/jpeg').split(',')[1];
    setUploadedImage(imageBase64);
    
    await performDetection(imageBase64);
  };

  const performDetection = async (imageBase64) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/ml/detect`, {
        image_base64: imageBase64,
        confidence_threshold: 0.7
      });
      
      if (response.data.success) {
        const detectedTools = response.data.results.detected_tools || [];
        setTools(detectedTools.map((tool, index) => ({
          id: index,
          class_name: tool.class_name,
          confidence: tool.confidence,
          detected_quantity: tool.detected_quantity,
          manual_quantity: tool.detected_quantity || 1,
          is_manual_edit: false
        })));
        
        alert(`Обнаружено ${detectedTools.length} инструментов!`);
      }
    } catch (error) {
      console.error('Ошибка детекции:', error);
      showError(ERROR_CODES.DETECTION_ERROR);
      setTools([]);
    } finally {
      setLoading(false);
    }
  };

  const handleImageUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = async (e) => {
        const base64 = e.target.result.split(',')[1];
        setUploadedImage(base64);
        await performDetection(base64);
      };
      reader.readAsDataURL(file);
    }
  };

  const startScanning = async () => {
    if (!engineer.trim()) {
      alert('Введите ФИО инженера');
      return;
    }

    setScanning(true);
    setLoading(true);

    try {
      const operationData = {
        engineer_name: engineer,
        operation_type: operationType,
        operation_date: operationDate,
        user_id: user.id
      };

      const token = localStorage.getItem('token');
      const headers = token !== 'demo-jwt-token' ? { Authorization: `Bearer ${token}` } : {};

      const response = await axios.post(`${API_BASE_URL}/operations/start`, operationData, { headers });
      setSessionId(response.data.session_id);
      
      await startCamera();
      
    } catch (error) {
      console.error('Ошибка начала операции:', error);
      showError(ERROR_CODES.OPERATION_START_ERROR);
      setSessionId(null);
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
      let finalImageBase64 = uploadedImage;
      
      if (!finalImageBase64 && videoRef.current && cameraActive) {
        const canvas = document.createElement('canvas');
        canvas.width = videoRef.current.videoWidth;
        canvas.height = videoRef.current.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(videoRef.current, 0, 0);
        finalImageBase64 = canvas.toDataURL('image/jpeg').split(',')[1];
      }

      const operationData = {
        session_id: sessionId,
        operation_date: operationDate,
        tools: tools.map(tool => ({
          tool_id: tool.id,
          final_quantity: tool.manual_quantity,
          was_manually_adjusted: tool.is_manual_edit
        })),
        image_base64: finalImageBase64
      };

      const token = localStorage.getItem('token');
      const headers = token !== 'demo-jwt-token' ? { Authorization: `Bearer ${token}` } : {};

      const response = await axios.post(`${API_BASE_URL}/operations/confirm`, operationData, { headers });
      
      stopCamera();
      
      alert(`Операция завершена! Обработано ${response.data.total_tools} инструментов`);
      resetOperation();
      
    } catch (error) {
      console.error('Ошибка подтверждения операции:', error);
      showError(ERROR_CODES.OPERATION_CONFIRM_ERROR);
    } finally {
      setLoading(false);
    }
  };

  const resetOperation = () => {
    setEngineer('');
    setTools([]);
    setSessionId(null);
    setScanning(false);
    setUploadedImage(null);
    stopCamera();
    
    const now = new Date();
    const localDateTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 16);
    setOperationDate(localDateTime);
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
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label>Тип операции:</label>
            <select
              value={operationType}
              onChange={(e) => setOperationType(e.target.value)}
              disabled={loading}
            >
              <option value="checkout">Выдача инструментов</option>
              <option value="checkin">Прием инструментов</option>
            </select>
          </div>

          <div className="form-group">
            <label>Дата и время операции:</label>
            <input
              type="datetime-local"
              value={operationDate}
              onChange={(e) => setOperationDate(e.target.value)}
              disabled={loading}
            />
          </div>

          <div className="action-buttons">
            <button 
              onClick={startScanning}
              disabled={!engineer.trim() || loading}
              className="scan-button"
            >
              {loading ? 'Подготовка...' : 'Начать операцию'}
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

        {/* Секция работы с камерой */}
        <div className="camera-section">
          <h3>Работа с камерой</h3>
          
          <div className="camera-controls">
            {!cameraActive ? (
              <button 
                onClick={startCamera} 
                disabled={!sessionId || loading}
                className="camera-button"
              >
                📷 Включить камеру
              </button>
            ) : (
              <>
                <button onClick={stopCamera} className="camera-button stop">
                  ⏹️ Выключить камеру
                </button>
                <button 
                  onClick={captureAndDetect} 
                  disabled={loading} 
                  className="camera-button capture"
                >
                  {loading ? '🔍 Распознавание...' : '📸 Распознать инструменты'}
                </button>
                
                <div className="file-upload">
                  <label htmlFor="image-upload" className="upload-button">
                    📁 Загрузить изображение
                  </label>
                  <input
                    id="image-upload"
                    type="file"
                    accept="image/*"
                    onChange={handleImageUpload}
                    style={{ display: 'none' }}
                  />
                </div>
              </>
            )}
          </div>

          {cameraActive && (
            <div className="video-container">
              <video 
                ref={videoRef}
                autoPlay 
                playsInline
                muted
                className="camera-video"
              />
              <div className="camera-overlay">
                <div className="scan-frame"></div>
                <p>Наведите камеру на инструменты</p>
              </div>
            </div>
          )}

          {uploadedImage && !cameraActive && (
            <div className="uploaded-image-preview">
              <p>📷 Изображение загружено</p>
              <button 
                onClick={() => performDetection(uploadedImage)} 
                disabled={loading} 
                className="camera-button capture"
              >
                {loading ? '🔍 Распознавание...' : '📸 Распознать инструменты'}
              </button>
            </div>
          )}
        </div>

        {tools.length > 0 && (
          <div className="tools-section">
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

// Компонент инструмента
function ToolItem({ tool, index, onQuantityChange, operationType }) {
  const [localQuantity, setLocalQuantity] = useState(tool.manual_quantity);

  const handleQuantityChange = (newQuantity) => {
    setLocalQuantity(newQuantity);
    onQuantityChange(index, newQuantity);
  };

  return (
    <div className={`tool-item ${tool.is_manual_edit ? 'manual-edit' : ''}`}>
      <div className="tool-info">
        <span className="tool-name">{tool.class_name}</span>
        {tool.confidence && (
          <span className="confidence">{tool.confidence.toFixed(1)}%</span>
        )}
      </div>
      
      <div className="quantity-controls">
        <button onClick={() => handleQuantityChange(localQuantity - 1)}>-</button>
        <input
          type="number"
          value={localQuantity}
          onChange={(e) => handleQuantityChange(parseInt(e.target.value) || 0)}
          min="0"
        />
        <button onClick={() => handleQuantityChange(localQuantity + 1)}>+</button>
      </div>
    </div>
  );
}

export default App;