-- Esquema de PostgreSQL: Sistema de Pronóstico de Siembra Adaptable

CREATE TABLE IF NOT EXISTS cultivos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    dias_crecimiento INTEGER NOT NULL,
    temperatura_min DECIMAL(5,2),
    temperatura_max DECIMAL(5,2),
    requerimiento_agua DECIMAL(5,2),
    resistencia_plagas DECIMAL(5,2),
    rendimiento_base DECIMAL(10,2),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS configuraciones (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    datos_deterministas JSONB NOT NULL,
    datos_estocasticos JSONB NOT NULL,
    datos_estado JSONB NOT NULL,
    factor_relevancia JSONB NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS historial_simulaciones (
    id SERIAL PRIMARY KEY,
    configuracion_id INTEGER REFERENCES configuraciones(id),
    nombre VARCHAR(150) DEFAULT '',
    fecha_optima DATE NOT NULL,
    kpi_esperado DECIMAL(10,2),
    probabilidad_exito DECIMAL(5,2),
    resultado_completo JSONB,
    fecha_ejecucion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS datos_externos (
    id SERIAL PRIMARY KEY,
    origen VARCHAR(100),
    datos JSONB NOT NULL,
    valido BOOLEAN DEFAULT TRUE,
    fecha_recepcion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS matrices_markov (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    tipo VARCHAR(50) NOT NULL, -- 'salud', 'enfermedad', 'crecimiento'
    estados JSONB NOT NULL,
    matriz_transicion JSONB NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bases creadas con una versión anterior: añade la columna de nombre.
ALTER TABLE historial_simulaciones ADD COLUMN IF NOT EXISTS nombre VARCHAR(150) DEFAULT '';

-- Perfiles de Factor de Relevancia (guardar, cargar, duplicar, compartir)
CREATE TABLE IF NOT EXISTS configuraciones_relevancia (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    autor VARCHAR(100) DEFAULT '',
    metodo VARCHAR(50) DEFAULT 'manual',  -- 'defecto', 'ley_minimo', 'historico', 'experto', 'campo', 'manual'
    notas TEXT DEFAULT '',
    pesos JSONB NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Diario de campo (experimentos simples del usuario)
CREATE TABLE IF NOT EXISTS registros_campo (
    id SERIAL PRIMARY KEY,
    temporada VARCHAR(50) NOT NULL,
    variable VARCHAR(50) NOT NULL,
    valor DECIMAL(12,3) NOT NULL,
    rendimiento DECIMAL(12,3) NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cultivos iniciales
INSERT INTO cultivos (nombre, dias_crecimiento, temperatura_min, temperatura_max, requerimiento_agua, resistencia_plagas, rendimiento_base)
SELECT * FROM (VALUES
    ('Maíz', 120, 15, 32, 5.0, 60, 8.0),
    ('Trigo', 140, 5, 24, 4.0, 55, 5.0),
    ('Papa', 100, 8, 22, 4.5, 40, 25.0),
    ('Arroz', 130, 20, 35, 8.0, 50, 6.0)
) AS v(nombre, dias, tmin, tmax, agua, resist, rend)
WHERE NOT EXISTS (SELECT 1 FROM cultivos);
