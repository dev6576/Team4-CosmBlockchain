import { Request, Response, NextFunction } from "express";

const errorHandler = (err: any, req: Request, res: Response, next: NextFunction) => {
  const statusCode = err.status || 500;
    res.status(statusCode).json({
      message: err.message,
      stack: err.stack,
    });
};
  
export default errorHandler;