import express ,{json,urlencoded} from 'express';
import router from './routes';
import  errorHandler from "./errorMiddleware";
import dotenv from 'dotenv';

dotenv.config();

const app = express();
const port = process.env.PORT;

app.use(json())
app.use(urlencoded({ extended: true }));

app.use("/oracle", router);
app.use(errorHandler);

app.listen(port, () => {
    console.log(`Server is listening on port ${port}`);
});