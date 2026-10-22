import express from 'express';

const app = express();
app.use(express.json());

// Health check: the platform calls it before sending traffic to a new version.
app.get('/healthz', (req, res) => res.send('ok'));

app.get('/api/hello', (req, res) => {
  res.json({ message: 'Hello from Inquir Compute', time: new Date().toISOString() });
});

// The platform sets PORT to runtime.port from inquir.yaml.
const port = Number(process.env.PORT) || 3000;
const server = app.listen(port, () => console.log(`listening on ${port}`));

// Finish open requests before a new version replaces this one.
process.on('SIGTERM', () => server.close(() => process.exit(0)));
