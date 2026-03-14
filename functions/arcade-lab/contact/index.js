import axios from "axios";
import querystring from "querystring";
import validator from "validator";
import { SSMClient, GetParametersCommand } from "@aws-sdk/client-ssm";
import { SESClient, SendEmailCommand } from "@aws-sdk/client-ses";

// Structured JSON logger
const log = (level, message, extra = {}) => {
  const entry = { timestamp: new Date().toISOString(), level, message, ...extra };
  const output = JSON.stringify(entry);
  if (level === "error") console.error(output);
  else if (level === "warn") console.warn(output);
  else console.log(output);
};

// Cache SSM secrets at init-phase (once per cold start)
let cachedParams = null;

const fetchSecrets = async () => {
  if (cachedParams) return cachedParams;

  const client = new SSMClient({ region: process.env.AWS_REGION });
  const input = {
    Names: [
      "/arcade-lab.io/contact/CF/SECRET_KEY",
      "/arcade-lab.io/contact/ses/TARGET",
      "/arcade-lab.io/contact/ses/SOURCE",
    ],
    WithDecryption: true,
  };
  const command = new GetParametersCommand(input);
  const { Parameters } = await client.send(command);

  const params = {};
  Parameters.forEach((el) => {
    const key = el.Name.split("/").pop();
    params[key] = el.Value;
  });

  cachedParams = params;
  log("info", "SSM parameters fetched and cached");
  return params;
};

// CF Turnstile validation
const validateCFTurnstile = async (token, secretKey) => {
  try {
    const { data } = await axios.post(
      "https://challenges.cloudflare.com/turnstile/v0/siteverify",
      querystring.stringify({
        secret: secretKey,
        response: token,
      }),
      {
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
      },
    );

    if (!data.success) {
      log("warn", "CF Turnstile validation failed", { errorCodes: data["error-codes"] });
    }
    return data.success;
  } catch (err) {
    log("error", "CF Turnstile validation error", { error: err.message });
    return null;
  }
};

// Send email using AWS SES
const sendEmail = async (params, name, email, message) => {
  const client = new SESClient({ region: process.env.AWS_REGION });

  const command = new SendEmailCommand({
    Destination: {
      ToAddresses: [params.TARGET],
    },
    Message: {
      Body: {
        Text: {
          Data: `You received a message from ${name} (${email})!\n\n${message}`,
        },
      },
      Subject: {
        Data: `Message from ${name} <${email}>`,
      },
    },
    Source: params.SOURCE,
  });

  try {
    const response = await client.send(command);
    log("info", "Email sent with SES", { messageId: response.MessageId });
    return true;
  } catch (err) {
    log("error", "SES email sending failed", { error: err.message });
    return false;
  }
};

// Lambda handler
export const handler = async (event) => {
  try {
    const { token, name, email, message } = event;

    // Basic validation
    if (
      !token ||
      !validator.isEmail(email) ||
      !validator.isLength(name, { min: 1, max: 100 }) ||
      !validator.isLength(message, { min: 1, max: 2000 })
    ) {
      log("warn", "Invalid input", { email, nameLength: name?.length, messageLength: message?.length });
      return {
        statusCode: 400,
        body: JSON.stringify({ message: "Invalid input." }),
      };
    }

    const params = await fetchSecrets();

    const isHuman = await validateCFTurnstile(token, params.SECRET_KEY);
    if (isHuman === null) {
      return {
        statusCode: 500,
        body: JSON.stringify({ message: "Internal server error." }),
      };
    }

    if (!isHuman) {
      return {
        statusCode: 403,
        body: JSON.stringify({ message: "Failed CF Turnstile verification." }),
      };
    }

    const emailSent = await sendEmail(params, name, email, message);
    if (!emailSent) {
      return {
        statusCode: 502,
        body: JSON.stringify({ message: "Failed to send email." }),
      };
    }

    log("info", "Contact form processed successfully", { email });
    return {
      statusCode: 200,
      body: JSON.stringify({ message: "Success!" }),
    };
  } catch (err) {
    log("error", "Unhandled exception", { error: err.message, stack: err.stack });
    return {
      statusCode: 500,
      body: JSON.stringify({ message: "Server error." }),
    };
  }
};
