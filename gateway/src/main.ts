import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

const WEAK_SECRETS = new Set([
  'dev-change-me',
  'changeme',
  'secret',
  'password',
  'test',
  'api_secret',
]);

function assertProductionConfig() {
  const env = (process.env.NODE_ENV ?? process.env.ENVIRONMENT ?? '').toLowerCase();
  if (env !== 'production') return;
  const secret = (process.env.API_SECRET ?? '').trim();
  if (secret.length < 32 || WEAK_SECRETS.has(secret.toLowerCase())) {
    throw new Error(
      'Production requires API_SECRET (min 32 characters, not a default value).',
    );
  }
}

async function bootstrap() {
  assertProductionConfig();
  const app = await NestFactory.create(AppModule);
  app.setGlobalPrefix('api');
  app.enableCors({
    origin: process.env.CORS_ORIGIN?.split(',') ?? true,
    credentials: true,
  });
  const port = parseInt(process.env.PORT ?? '3001', 10);
  await app.listen(port);
  console.log(`Gateway listening on http://localhost:${port}/api`);
}

bootstrap();
