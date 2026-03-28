import { Body, Controller, Get, Post, Res, UseGuards } from '@nestjs/common';
import { Response } from 'express';
import { AuthGuard } from './auth.guard';
import { OrchestratorProxyService } from './orchestrator-proxy.service';

@Controller()
@UseGuards(AuthGuard)
export class OrchestratorProxyController {
  constructor(private readonly proxy: OrchestratorProxyService) {}

  @Get('v1/signals')
  async signals(@Res() res: Response) {
    const { status, data } = await this.proxy.forward('GET', '/v1/signals');
    return res.status(status).json(data);
  }

  @Get('v1/control/status')
  async controlStatus(@Res() res: Response) {
    const { status, data } = await this.proxy.forward(
      'GET',
      '/v1/control/status',
    );
    return res.status(status).json(data);
  }

  @Post('v1/control/trading')
  async setTrading(@Body() body: Record<string, unknown>, @Res() res: Response) {
    const { status, data } = await this.proxy.forward(
      'POST',
      '/v1/control/trading',
      body,
    );
    return res.status(status).json(data);
  }

  @Post('v1/pipeline/tick')
  async tick(@Res() res: Response) {
    const { status, data } = await this.proxy.forward('POST', '/v1/pipeline/tick');
    return res.status(status).json(data);
  }
}
