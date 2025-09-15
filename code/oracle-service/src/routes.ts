import express from 'express';
import cors from 'cors';
const router = express.Router();
router.use(cors())
import {
    getOracleData, updateOracleData
} from "./controller";


// execute
router.route('/oracle-data').post(updateOracleData);

// queries
router.route('/oracle-data').get(getOracleData);

export default router;