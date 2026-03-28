import { HttpService } from '@nestjs/axios';
import { Injectable, ServiceUnavailableException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { firstValueFrom } from 'rxjs';

@Injectable()
export class OrchestratorProxyService {
  private readonly base: string;

  constructor(
    private readonly http: HttpService,
    private readonly config: ConfigService,
  ) {
    this.base = (
      this.config.get<string>('ORCHESTRATOR_URL') ?? 'http://127.0.0.1:8000'
    ).replace(/\/$/, '');
  }

  private headers() {
    const secret = this.config.get<string>('API_SECRET');
    const h: Record<string, string> = {};
    if (secret) {
      h['Authorization'] = `Bearer ${secret}`;
    }
    return h;
  }

  async forward(method: string, path: string, body?: unknown) {
    const url = `${this.base}${path}`;
    try {
      const res = await firstValueFrom(
        this.http.request({
          method,
          url,
          data: body,
          headers: this.headers(),
          validateStatus: () => true,
        }),
      );
      return { status: res.status, data: res.data };
    } catch {
      throw new ServiceUnavailableException('Orchestrator unreachable');
    }
  }
}
