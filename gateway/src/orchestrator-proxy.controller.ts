import { Body, Controller, Get, Post, Req, Res, UseGuards } from '@nestjs/common';
import { Request, Response } from 'express';
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

  @Get('v1/broker/status')
  async brokerStatus(@Res() res: Response) {
    const { status, data } = await this.proxy.forward('GET', '/v1/broker/status');
    return res.status(status).json(data);
  }

  @Post('v1/broker/orders/place')
  async brokerPlaceOrder(
    @Body() body: Record<string, unknown>,
    @Res() res: Response,
  ) {
    const { status, data } = await this.proxy.forward(
      'POST',
      '/v1/broker/orders/place',
      body,
    );
    return res.status(status).json(data);
  }

  private querySuffix(req: Request): string {
    const i = req.originalUrl.indexOf('?');
    return i >= 0 ? req.originalUrl.substring(i) : '';
  }

  @Get('v1/broker/orders')
  async brokerOrders(@Req() req: Request, @Res() res: Response) {
    const { status, data } = await this.proxy.forward(
      'GET',
      `/v1/broker/orders${this.querySuffix(req)}`,
    );
    return res.status(status).json(data);
  }

  @Get('v1/broker/holdings')
  async brokerHoldings(@Res() res: Response) {
    const { status, data } = await this.proxy.forward('GET', '/v1/broker/holdings');
    return res.status(status).json(data);
  }

  @Get('v1/broker/orders/status')
  async brokerOrderStatus(@Req() req: Request, @Res() res: Response) {
    const { status, data } = await this.proxy.forward(
      'GET',
      `/v1/broker/orders/status${this.querySuffix(req)}`,
    );
    return res.status(status).json(data);
  }

  @Post('v1/broker/margins/preview')
  async brokerMargins(
    @Body() body: Record<string, unknown>,
    @Res() res: Response,
  ) {
    const { status, data } = await this.proxy.forward(
      'POST',
      '/v1/broker/margins/preview',
      body,
    );
    return res.status(status).json(data);
  }

  @Post('v1/broker/orders/cancel')
  async brokerCancel(
    @Body() body: Record<string, unknown>,
    @Res() res: Response,
  ) {
    const { status, data } = await this.proxy.forward(
      'POST',
      '/v1/broker/orders/cancel',
      body,
    );
    return res.status(status).json(data);
  }

  @Post('v1/broker/orders/modify')
  async brokerModify(
    @Body() body: Record<string, unknown>,
    @Res() res: Response,
  ) {
    const { status, data } = await this.proxy.forward(
      'POST',
      '/v1/broker/orders/modify',
      body,
    );
    return res.status(status).json(data);
  }

  @Post('v1/ml/sentiment')
  async mlSentiment(
    @Body() body: Record<string, unknown>,
    @Res() res: Response,
  ) {
    const { status, data } = await this.proxy.forward(
      'POST',
      '/v1/ml/sentiment',
      body,
    );
    return res.status(status).json(data);
  }
}
