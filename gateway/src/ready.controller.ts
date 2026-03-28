import { Controller, Get, Res } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { ConfigService } from '@nestjs/config';
import { Response } from 'express';
import { firstValueFrom } from 'rxjs';

@Controller('ready')
export class ReadyController {
  constructor(
    private readonly http: HttpService,
    private readonly config: ConfigService,
  ) {}

  @Get()
  async ready(@Res() res: Response) {
    const base = (
      this.config.get<string>('ORCHESTRATOR_URL') ?? 'http://127.0.0.1:8000'
    ).replace(/\/$/, '');
    try {
      const r = await firstValueFrom(
        this.http.get(`${base}/ready`, {
          timeout: 8000,
          validateStatus: () => true,
        }),
      );
      if (r.status >= 400) {
        return res.status(503).json({
          ready: false,
          gateway: 'ok',
          orchestrator: r.data,
        });
      }
      return res.status(200).json({
        ready: true,
        gateway: 'ok',
        orchestrator: r.data,
      });
    } catch {
      return res.status(503).json({
        ready: false,
        gateway: 'ok',
        orchestrator: 'unreachable',
      });
    }
  }
}
