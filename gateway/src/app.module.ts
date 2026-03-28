import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { HttpModule } from '@nestjs/axios';
import { HealthController } from './health.controller';
import { ReadyController } from './ready.controller';
import { OrchestratorProxyController } from './orchestrator-proxy.controller';
import { OrchestratorProxyService } from './orchestrator-proxy.service';
import { AuthGuard } from './auth.guard';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }),
    HttpModule.register({
      timeout: 15000,
      maxRedirects: 3,
    }),
  ],
  controllers: [HealthController, ReadyController, OrchestratorProxyController],
  providers: [OrchestratorProxyService, AuthGuard],
})
export class AppModule {}
